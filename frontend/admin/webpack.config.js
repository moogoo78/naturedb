const path = require('path');

const moduleRules = {
  rules: [
    {
      test: /\.js$/,
      exclude: /node_modules/,
      loader: 'babel-loader'
    }
  ],
};

module.exports = (env) => {
  const target = (env.prod) ? 'build' : '../../app/blueprints/static_admin';
  const envExt = (env.prod) ? '.min.js' : '.dev.js';
  return [
    {
      entry: {
        'record': './src/record-form.js',
      },
      output: {
        path: path.join(__dirname, target),
        filename: `[name]${envExt}`,
      },
      module: moduleRules,
      devtool: 'eval-source-map'
    },
    // {
    //   entry: {
    //     'search': './src/data-search.js',
    //   },
    //   output: {
    //     path: path.join(__dirname, '../app/static/js'),
    //     filename: `[name]${envExt}`,
    //   },
    //   module: moduleRules,
    //   devtool: 'eval-source-map'
    // },
  ];


};
