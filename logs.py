#!/usr/bin/env python3
"""
Log analysis and grading system for AI chat sessions.
Analyzes conversation quality and provides metrics for model performance.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import statistics


class LogAnalyzer:
    def __init__(self, logs_dir="logs"):
        self.logs_dir = Path(logs_dir)
        self.quality_weights = {
            "coherence": 0.25,      # Does response match input?
            "relevance": 0.25,      # Is it on-topic?
            "completeness": 0.20,   # Is response complete/cut off?
            "creativity": 0.15,     # Original vs repetitive?
            "safety": 0.15,         # Appropriate content?
        }
        
        # Quality indicators
        self.good_indicators = {
            "direct_response": [r"thank you", r"yes", r"no", r"i (?:am|can|will|don't)", r"here (?:is|are)"],
            "helpful_tone": [r"how can i help", r"i'd be happy", r"certainly", r"of course"],
            "coherent_structure": [r"\w+[.!?]\s+[A-Z]", r"first", r"second", r"finally", r"however"],
            "appropriate_length": lambda text: 10 <= len(text.split()) <= 200,
            "no_repetition": lambda text: not self._has_repetition(text),
        }
        
        self.bad_indicators = {
            "hallucination": [r"covid-19", r"pandemic", r"statistics", r"studies show", r"according to"],
            "depression_markers": [r"misery", r"pain", r"disaster", r"giving up", r"fuck.*shit", r"time.*world"],
            "incoherent": [r"#include", r"int main", r"cout", r"printf"] + [r"[a-zA-Z]{20,}"],  # Code when not requested
            "cut_off": [r"\.\.\.+$", r"\w+$(?<![.!?])"],  # Ends mid-sentence
            "meta_statements": [r"as an ai", r"i am an ai", r"i'm an ai assistant"],
            "refusals": [r"i (?:can't|cannot|won't)", r"sorry,? i (?:can't|cannot)"],
        }
    
    def _has_repetition(self, text: str) -> bool:
        """Check for excessive repetition in text."""
        words = text.lower().split()
        if len(words) < 4:
            return False
        
        # Check for repeated phrases
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            if text.lower().count(phrase) > 2:
                return True
        
        # Check for repeated single words
        word_counts = {}
        for word in words:
            if len(word) > 3:  # Only count substantial words
                word_counts[word] = word_counts.get(word, 0) + 1
                if word_counts[word] > len(words) * 0.2:  # >20% repetition
                    return True
        
        return False
    
    def _extract_conversations(self, log_content: str) -> List[Tuple[str, str]]:
        """Extract user input and AI response pairs from log content."""
        conversations = []
        lines = log_content.split('\n')
        current_user = None
        current_ai = None
        
        for line in lines:
            line = line.strip()
            
            # Extract user input
            if line.startswith('You: '):
                current_user = line[5:].strip()
                current_ai = None
                
            # Extract AI response from stdout or direct AI: lines
            elif line.startswith('[llama.cpp-stdout] '):
                if current_user:
                    current_ai = line[19:].strip()  # Remove prefix
                    
            elif line.startswith('AI: '):
                if current_user:
                    current_ai = line[4:].strip()
                    
            # Save complete conversation pairs
            if current_user and current_ai:
                # Skip empty or very short responses
                if len(current_ai.strip()) > 3:
                    conversations.append((current_user, current_ai))
                current_user = None
                current_ai = None
        
        return conversations
    
    def _score_response(self, user_input: str, ai_response: str) -> Dict[str, float]:
        """Score a single AI response across multiple dimensions."""
        scores = {}
        
        # Coherence: Does response relate to input?
        coherence_score = 0.5  # Default neutral
        
        # Check if response addresses input
        user_words = set(user_input.lower().split())
        response_words = set(ai_response.lower().split())
        
        if len(user_words & response_words) > 0:
            coherence_score += 0.3
        
        # Check for good indicators
        for indicator_type, patterns in self.good_indicators.items():
            if callable(patterns):
                if patterns(ai_response):
                    coherence_score += 0.1
            else:
                for pattern in patterns:
                    if re.search(pattern, ai_response.lower()):
                        coherence_score += 0.1
                        break
        
        scores["coherence"] = min(1.0, coherence_score)
        
        # Relevance: On-topic response
        relevance_score = 0.6  # Default slightly positive
        
        # Penalize for bad indicators
        for indicator_type, patterns in self.bad_indicators.items():
            for pattern in patterns:
                if re.search(pattern, ai_response.lower()):
                    relevance_score -= 0.2
                    break
        
        scores["relevance"] = max(0.0, relevance_score)
        
        # Completeness: Is response complete?
        completeness_score = 0.8  # Default high
        
        if re.search(r"\.\.\.+$", ai_response) or not ai_response.endswith(('.', '!', '?', '"', "'")):
            completeness_score -= 0.3
        
        scores["completeness"] = max(0.0, completeness_score)
        
        # Creativity: Novel vs repetitive
        creativity_score = 0.7  # Default good
        
        if self._has_repetition(ai_response):
            creativity_score -= 0.4
        
        if len(set(ai_response.lower().split())) / max(1, len(ai_response.split())) > 0.7:
            creativity_score += 0.2  # High word diversity
        
        scores["creativity"] = max(0.0, min(1.0, creativity_score))
        
        # Safety: Appropriate content
        safety_score = 0.9  # Default very safe
        
        # Check for concerning content
        concerning_patterns = [
            r"fuck.*shit.*misery", r"disaster.*pain", r"giving up.*world"
        ]
        
        for pattern in concerning_patterns:
            if re.search(pattern, ai_response.lower()):
                safety_score -= 0.3
        
        scores["safety"] = max(0.0, safety_score)
        
        return scores
    
    def _calculate_weighted_score(self, scores: Dict[str, float]) -> float:
        """Calculate final weighted score from dimension scores."""
        total_score = 0
        for dimension, score in scores.items():
            weight = self.quality_weights.get(dimension, 0)
            total_score += score * weight
        return total_score
    
    def analyze_log_file(self, log_file: Path) -> Dict:
        """Analyze a single log file and return quality metrics."""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {"error": f"Failed to read {log_file}: {e}"}
        
        conversations = self._extract_conversations(content)
        
        if not conversations:
            return {
                "file": log_file.name,
                "conversations": 0,
                "overall_score": 0.0,
                "grade": "F",
                "issues": ["No conversations found"]
            }
        
        all_scores = []
        detailed_scores = []
        
        for user_input, ai_response in conversations:
            scores = self._score_response(user_input, ai_response)
            weighted_score = self._calculate_weighted_score(scores)
            all_scores.append(weighted_score)
            
            detailed_scores.append({
                "user": user_input[:50] + "..." if len(user_input) > 50 else user_input,
                "ai": ai_response[:100] + "..." if len(ai_response) > 100 else ai_response,
                "scores": scores,
                "weighted_score": weighted_score
            })
        
        # Calculate overall metrics
        overall_score = statistics.mean(all_scores) if all_scores else 0.0
        
        # Assign letter grade
        if overall_score >= 0.9:
            grade = "A+"
        elif overall_score >= 0.8:
            grade = "A"
        elif overall_score >= 0.7:
            grade = "B"
        elif overall_score >= 0.6:
            grade = "C"
        elif overall_score >= 0.5:
            grade = "D"
        else:
            grade = "F"
        
        # Identify main issues
        issues = []
        if overall_score < 0.6:
            avg_scores = {}
            for dim in self.quality_weights.keys():
                dim_scores = [conv["scores"][dim] for conv in detailed_scores]
                avg_scores[dim] = statistics.mean(dim_scores) if dim_scores else 0
            
            for dim, score in avg_scores.items():
                if score < 0.5:
                    issues.append(f"Poor {dim}")
        
        return {
            "file": log_file.name,
            "timestamp": log_file.stat().st_mtime,
            "conversations": len(conversations),
            "overall_score": round(overall_score, 3),
            "grade": grade,
            "detailed_scores": detailed_scores,
            "issues": issues
        }
    
    def analyze_all_logs(self) -> Dict:
        """Analyze all log files in the logs directory."""
        if not self.logs_dir.exists():
            return {"error": f"Logs directory {self.logs_dir} not found"}
        
        log_files = list(self.logs_dir.glob("session-*.log"))
        
        if not log_files:
            return {"error": "No session log files found"}
        
        results = []
        
        for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True):
            result = self.analyze_log_file(log_file)
            results.append(result)
        
        # Calculate summary statistics
        valid_results = [r for r in results if "error" not in r and r["conversations"] > 0]
        
        if not valid_results:
            return {"error": "No valid conversations found in any logs"}
        
        scores = [r["overall_score"] for r in valid_results]
        grades = [r["grade"] for r in valid_results]
        
        summary = {
            "total_sessions": len(results),
            "valid_sessions": len(valid_results),
            "average_score": round(statistics.mean(scores), 3),
            "median_score": round(statistics.median(scores), 3),
            "best_session": max(valid_results, key=lambda x: x["overall_score"]),
            "worst_session": min(valid_results, key=lambda x: x["overall_score"]),
            "grade_distribution": {grade: grades.count(grade) for grade in set(grades)},
            "recent_trend": self._calculate_trend(valid_results[-5:]) if len(valid_results) >= 3 else "Insufficient data"
        }
        
        return {
            "summary": summary,
            "sessions": results,
            "analysis_time": datetime.now().isoformat()
        }
    
    def _calculate_trend(self, recent_results: List[Dict]) -> str:
        """Calculate trend from recent sessions."""
        if len(recent_results) < 3:
            return "Insufficient data"
        
        scores = [r["overall_score"] for r in recent_results]
        first_half = statistics.mean(scores[:len(scores)//2])
        second_half = statistics.mean(scores[len(scores)//2:])
        
        diff = second_half - first_half
        
        if diff > 0.1:
            return "Improving"
        elif diff < -0.1:
            return "Declining"
        else:
            return "Stable"
    
    def get_best_conversations(self, min_score=0.8, limit=10) -> List[Dict]:
        """Get the highest quality conversations for reference."""
        analysis = self.analyze_all_logs()
        
        if "error" in analysis:
            return []
        
        all_conversations = []
        
        for session in analysis["sessions"]:
            if "detailed_scores" in session:
                for conv in session["detailed_scores"]:
                    if conv["weighted_score"] >= min_score:
                        conv["session"] = session["file"]
                        all_conversations.append(conv)
        
        # Sort by score and return top conversations
        all_conversations.sort(key=lambda x: x["weighted_score"], reverse=True)
        return all_conversations[:limit]
    
    def export_analysis(self, filename="log_analysis.json"):
        """Export full analysis to JSON file."""
        analysis = self.analyze_all_logs()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"Analysis exported to {filename}")
        return analysis


def main():
    """Command line interface for log analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze AI chat session logs")
    parser.add_argument("--logs-dir", default="logs", help="Directory containing log files")
    parser.add_argument("--export", action="store_true", help="Export analysis to JSON")
    parser.add_argument("--best", type=int, metavar="N", help="Show N best conversations")
    parser.add_argument("--recent", action="store_true", help="Show recent sessions only")
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer(args.logs_dir)
    
    if args.best:
        print(f"🏆 Top {args.best} Conversations:")
        print("=" * 50)
        
        best_conversations = analyzer.get_best_conversations(limit=args.best)
        
        for i, conv in enumerate(best_conversations, 1):
            print(f"\n{i}. Score: {conv['weighted_score']:.3f} ({conv['session']})")
            print(f"   User: {conv['user']}")
            print(f"   AI: {conv['ai']}")
            
    else:
        analysis = analyzer.analyze_all_logs()
        
        if "error" in analysis:
            print(f"❌ Error: {analysis['error']}")
            return
        
        summary = analysis["summary"]
        
        print("📊 Log Analysis Summary")
        print("=" * 40)
        print(f"Sessions analyzed: {summary['valid_sessions']}/{summary['total_sessions']}")
        print(f"Average quality: {summary['average_score']:.3f}")
        print(f"Recent trend: {summary['recent_trend']}")
        print(f"\n🎯 Best session: {summary['best_session']['file']} (Score: {summary['best_session']['overall_score']:.3f}, Grade: {summary['best_session']['grade']})")
        print(f"⚠️  Worst session: {summary['worst_session']['file']} (Score: {summary['worst_session']['overall_score']:.3f}, Grade: {summary['worst_session']['grade']})")
        
        print(f"\n📈 Grade Distribution:")
        for grade, count in sorted(summary['grade_distribution'].items()):
            print(f"   {grade}: {count}")
        
        if args.recent:
            print(f"\n📅 Recent Sessions:")
            for session in analysis["sessions"][:5]:
                if "error" not in session and "timestamp" in session:
                    timestamp = datetime.fromtimestamp(session["timestamp"]).strftime("%m-%d %H:%M")
                    issues_str = ", ".join(session["issues"]) if session["issues"] else "No issues"
                    print(f"   {session['file']} | {timestamp} | {session['grade']} ({session['overall_score']:.3f}) | {issues_str}")
        
        if args.export:
            analyzer.export_analysis()


if __name__ == "__main__":
    main()