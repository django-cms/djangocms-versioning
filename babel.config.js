module.exports = {
    presets: [
        ['@babel/preset-env', {
            targets: {
                browsers: ['last 2 versions', '> 1%']
            }
        }]
    ],
    plugins: [
        '@babel/plugin-syntax-dynamic-import'
    ]
};
