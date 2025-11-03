// #####################################################################################################################
// #IMPORTS#
var gulp = require('gulp');
var gutil = require('gulp-util');
var plumber = require('gulp-plumber');
var gulpif = require('gulp-if');
var eslint = require('gulp-eslint-new');
var webpack = require('webpack');

var argv = require('minimist')(process.argv.slice(2)); // eslint-disable-line

// #####################################################################################################################
// #SETTINGS#
var options = {
    debug: argv.debug
};
var PROJECT_ROOT = __dirname + '/djangocms_versioning/static/djangocms_versioning';
var PROJECT_PATH = {
    js: PROJECT_ROOT + '/js',
    sass: PROJECT_ROOT + '/sass',
    css: PROJECT_ROOT + '/css',
};

var PROJECT_PATTERNS = {
    js: [
        PROJECT_PATH.js + '/*.js',
        '!' + PROJECT_PATH.js + '/dist/*.js'
    ],
    sass: [
        PROJECT_PATH.sass + '/**/*.{scss,sass}'
    ],
    icons: [
        PROJECT_PATH.icons + '/src/*.svg'
    ]
};

gulp.task('lint:javascript', function () {
    // DOCS: http://eslint.org
    return gulp.src(PROJECT_PATTERNS.js)
        .pipe(gulpif(!process.env.CI, plumber()))
        .pipe(eslint())
        .pipe(eslint.format())
        .pipe(eslint.failAfterError())
        .pipe(gulpif(!process.env.CI, plumber.stop()));
});

gulp.task('lint', gulp.series('lint:javascript'));


var webpackBundle = function (opts) {
    var webpackOptions = opts || {};

    webpackOptions.PROJECT_PATH = PROJECT_PATH;
    webpackOptions.debug = options.debug;

    return function (done) {
        var config = require('./webpack.config')(webpackOptions);

        webpack(config, function (err, stats) {
            if (err) {
                console.error('[webpack] Error:', err);
                if (done) {
                    done(err);
                }
                return;
            }
            console.log('[webpack]', stats.toString({
                colors: true,
                modules: false,
                children: false,
                chunks: false,
                chunkModules: false
            }));
            if (typeof done !== 'undefined' && (!opts || !opts.watch)) {
                done();
            }
        });
    };
};

gulp.task('bundle:watch', webpackBundle({ watch: true }));
gulp.task('bundle', webpackBundle());
gulp.task('build', gulp.series('bundle'));

gulp.task('watch', function (done) {
    gulp.series('bundle:watch')();
    gulp.watch(PROJECT_PATTERNS.js, gulp.series('lint'));
    done();
});

gulp.task('default', gulp.series('watch'));
