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
        mode: debug ? 'development' : 'production',
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
        },
        performance: {
            hints: false,
            maxEntrypointSize: 512000,
            maxAssetSize: 512000
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
                                presets: ['@babel/preset-env'],
                            },
                        },
                    ],
                    exclude: /(node_modules|libs|tidy|addons\/jquery.*)/,
                },
                {
                    test: /(.html$|api\/dom)/,
                    type: 'asset/source',
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
                                postcssOptions: {
                                    plugins: [
                                        require('autoprefixer'),
                                        require('cssnano')(),
                                    ],
                                },
                            },
                        },
                    ],
                },
            ],
        },
        stats: {
            preset: 'normal',
            reasons: false,
            modulesSpace: 15,
            errorDetails: true
        },
        optimization: {
            concatenateModules: true,
            providedExports: true,
            usedExports: true
        }
    };

    if (debug) {
        baseConfig.devtool = 'cheap-module-source-map';
        baseConfig.plugins = baseConfig.plugins.concat([
            new webpack.DefinePlugin({
                __DEV__: 'true',
            }),
        ]);
    } else {
        baseConfig.plugins = baseConfig.plugins.concat([
            new webpack.DefinePlugin({
                __DEV__: 'false',
            }),
        ]);
    }

    return baseConfig;
};
