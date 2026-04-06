var createError = require('http-errors');
var express = require('express');
var path = require('path');
var cookieParser = require('cookie-parser');
var logger = require('morgan');

var chatRouter = require('./routes/chat');
var fs = require('fs');

var app = express();

// view engine setup
app.set('views', path.join(__dirname, 'views'));
app.set('view engine', 'pug');

app.use(logger('dev'));
app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(express.static(path.join(__dirname, 'public')));

// API: Get available characters and LLMs
app.get('/api/config', (req, res) => {
  try {
    const configData = JSON.parse(fs.readFileSync('characters.json', 'utf8'));
    const config = JSON.parse(fs.readFileSync('config.json', 'utf8'));
    
    res.json({
      characters: configData.characters,
      llms: configData.llms,
      current_character: config.current_character || 'kara',
      current_llm: config.current_llm || 'dolphin'
    });
  } catch (err) {
    console.error('Error loading config:', err);
    res.status(500).json({ error: 'Failed to load configuration' });
  }
});

// Home page
app.get('/', (req, res) => {
  res.render('index', { title: 'Kara Chat', characterName: 'Kara' });
});

// Chat API routes
app.use('/api/chat', chatRouter);

// catch 404 and forward to error handler
app.use(function(req, res, next) {
  next(createError(404));
});

// error handler
app.use(function(err, req, res, next) {
  // set locals, only providing error in development
  res.locals.message = err.message;
  res.locals.error = req.app.get('env') === 'development' ? err : {};

  // render the error page
  res.status(err.status || 500);
  res.render('error');
});

module.exports = app;
