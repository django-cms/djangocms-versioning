var webpack = require('webpack');
// var path = require('path');

module.exports = function(opts) {
    'use strict';

    var PROJECT_PATH = opts.PROJECT_PATH;
    var debug = opts.debug;

    if (!debug) {
        process.env.NODE_ENV = 'production';
    }

    var baseConfig = {
        devtool: false,
        watch: !!opts.watch,
        entry: {
            // CMS frontend
            versioning: PROJECT_PATH.js + '/base.js',
        },
        output: {
            path: PROJECT_PATH.js + '/dist/',
            filename: 'bundle.[name].min.js',
            chunkFilename: 'bundle.[name].min.js',
            jsonpFunction: 'versioningWebpackJsonp',
        },
        plugins: [],
        resolve: {
            alias: {
                htmldiff: PROJECT_PATH.js + '/libs/htmldiff.js',
                prettydiff: PROJECT_PATH.js + '/prettydiff.js',
            },
        },
        module: {
            rules: [
                // must be first
                {
                    test: /\.js$/,
                    use: [
                        {
                            loader: 'babel-loader',
                            options: {
                                retainLines: true,
                            },
                        },
                    ],
                    exclude: /(node_modules|libs|tidy|addons\/jquery.*)/,
                },
                {
                    test: /(.html$|api\/dom)/,
                    use: [
                        {
                            loader: 'raw-loader',
                        },
                    ],
                },
                {
                    test: /(.css$)/,
                    use: [
                        {
                            loader: 'raw-loader',
                        },
                        {
                            loader: 'postcss-loader',
                            options: {
                                plugins: () => [
                                    require('autoprefixer')({
                                        browsers: ['last 2 versions', '> 1%'],
                                    }),
                                    require('cssnano')(),
                                ],
                            },
                        },
                    ],
                },
            ],
        },
        stats: 'verbose',
    };

    if (debug) {
        baseConfig.devtool = 'cheap-module-eval-source-map';
        baseConfig.plugins = baseConfig.plugins.concat([
            new webpack.NoEmitOnErrorsPlugin(),
            new webpack.DefinePlugin({
                __DEV__: 'true',
            }),
        ]);
    } else {
        baseConfig.plugins = baseConfig.plugins.concat([
            new webpack.DefinePlugin({
                __DEV__: 'false',
            }),
            new webpack.optimize.ModuleConcatenationPlugin(),
            new webpack.optimize.UglifyJsPlugin({
                comments: false,
                compressor: {
                    drop_console: true, // eslint-disable-line
                },
            }),
        ]);
    }

    return baseConfig;
};
