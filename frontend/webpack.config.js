const path = require('path');

module.exports = (env) => {
  //const env_name = (env.prod) ? '.min.js' : '.dev.js';
  const env_name = '.min.js';
  return {
    entry: {
      'record': './src/record-form.js',
    },
    output: {
      path: path.join(__dirname, '../app/static_admin'),
      filename: `[name]${env_name}`,
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
