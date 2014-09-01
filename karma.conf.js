module.exports = function(config) {
  config.set({
    basePath: 'static/js',
    frameworks: ['qunit'],
    plugins: [
      'karma-qunit',
      'karma-chrome-launcher',
      'karma-ember-preprocessor',
      'karma-phantomjs-launcher'
    ],
    files: [
      'lib/jquery-1.10.2.js',
      'lib/bootstrap.min.js',
      'lib/handlebars-1.1.2.js',
      'lib/ember-1.7.0.js',
      'lib/ember-data-1.0.0-beta9.js',
      'lib/socket.io-0.9.16.js',
      'lib/jquery-mockjax-1.5.4.js',
      'app.js',
      'tests/*.js',
      'templates/*.hbs'
    ],
    exclude: [ ],
    preprocessors: {
      '**/*.hbs': 'ember'
    },
    reporters: ['progress'],
    port: 9876,
    proxies: {
        '/api': 'http://localhost:5000/api',
        '/static': 'http://localhost:5000/static',
    },
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: true,
    browsers: ['Chrome'],
    singleRun: false
  });
};
