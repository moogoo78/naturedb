const path = require('path');

module.exports = (env) => {
  const target = (env.prod) ? 'build' : '../app/static_admin';
  const envExt = (env.prod) ? '.min.js' : '.dev.js';
  return {
    entry: {
      'record': './src/record-form.js',
    },
    output: {
      path: path.join(__dirname, target),
      filename: `[name]${envExt}`,
    },
    module: {
      rules: [
        {
	    test: /\.js$/,
	    exclude: /node_modules/,
	    loader: 'babel-loader'
	}
      ],
    },
    devtool: 'eval-source-map'
  };
};
