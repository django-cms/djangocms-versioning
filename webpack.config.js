const path = require('path');
const webpack = require('webpack');

const JS_PATH = path.join(__dirname, 'djangocms_versioning/static/djangocms_versioning/js');

module.exports = (env, argv) => {
    const debug = argv && argv.mode === 'development';

    if (!debug) {
        process.env.NODE_ENV = 'production';
    }

    const config = {
        mode: debug ? 'development' : 'production',
        devtool: debug ? 'cheap-module-source-map' : false,
        entry: {
            versioning: path.join(JS_PATH, 'base.js'),
        },
        output: {
            path: path.join(JS_PATH, 'dist/'),
            filename: 'bundle.[name].min.js',
            chunkFilename: 'bundle.[name].min.js',
        },
        performance: {
            hints: false,
            maxEntrypointSize: 512000,
            maxAssetSize: 512000,
        },
        plugins: [
            new webpack.DefinePlugin({
                __DEV__: debug ? 'true' : 'false',
            }),
        ],
        resolve: {
            alias: {
                htmldiff: path.join(JS_PATH, 'libs/htmldiff.js'),
                prettydiff: path.join(JS_PATH, 'prettydiff.js'),
            },
        },
        module: {
            rules: [
                {
                    test: /\.js$/,
                    use: [
                        {
                            loader: 'babel-loader',
                            options: {
                                presets: ['@babel/preset-env'],
                                plugins: process.env.COVERAGE === 'true' ? ['istanbul'] : [],
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
                        { loader: 'raw-loader' },
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
            errorDetails: true,
        },
        optimization: {
            concatenateModules: true,
            providedExports: true,
            usedExports: true,
        },
    };

    return config;
};
