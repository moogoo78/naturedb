// Setnil DOM helper


// inspried from https://stackoverflow.com/a/49508882/644070
const createElementWithAttributes = (name, ...args) => {

  const e = document.createElement(name);
  args.forEach(arg => {
    if (arg instanceof HTMLElement) {
      e.appendChild(arg);
    } else if (typeof arg == 'string') {
      e.appendChild(document.createTextNode(arg));
    } else {
      Object.entries(arg).forEach(([key, value]) => e.setAttribute(key, value));
    }
  });
  return e;
};

const findElements = (key) => {
  if (key.indexOf('#') >=0) {
    return document.getElementById(key.substring(1));
  } else if (key.indexOf('.') >=0) {
    return document.getElementsByClassName(key.substring(1));
  }
};

const Setnil = (() => {
  const api = {};

  api.e = createElementWithAttributes;
  api.find = findElements;

  return api;
})();

export default Setnil;
