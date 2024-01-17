/** Common Snail

  example:
  ```
  const html = o_.make(
    'div', {
      "class":"uk-alert-danger", "uk-alert": "", onclick: (e) => {e.stopPropagation();e.preventDefault();  console.log('uuu');}
    },
    o_.make(
      'a',
      {"class": "uk-alert-close", "uk-close": ""}),
    o_.make(
      'div',
      o_.make('p', 'aaaaa'),
      {onclick: (e) => {console.log('uuao');}}
    ),
  );
  console.log(html);
  const fooEle = document.getElementById('xx');
  fooEle.appendChild(html);
  ```
 */

// inspried from https://stackoverflow.com/a/49508882/644070
const createElementWithAttributes = (name, ...args) => {
  const e = document.createElement(name);
  args.forEach(arg => {
    if (arg instanceof HTMLElement) {
      e.appendChild(arg);
    } else if (typeof arg == 'string') {
      e.appendChild(document.createTextNode(arg));
    } else {
      Object.entries(arg).forEach(([key, value]) => {
        e[key] = value;
        if (typeof value === 'function') {
        } else {
          e.setAttribute(key, value);
        }
      });
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

const fetchData = (endpoint) => {
  const headers = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    'X-Requested-With': 'XMLHttpRequest'
  };

  return fetch(endpoint, {
    method: "GET",
    cache: "no-cache",
    credentials: "same-origin",
    headers: headers,
  })
    .then(response => response.json())
    .then(json => {
      return Promise.resolve(json);
    })
    .catch(error => { throw new Error(`fetch error: ${error}`) });
};

const CommonSnail = (() => {
  const api = {};

  api.make = createElementWithAttributes;
  api.find = findElements;
  api.fetch = fetchData;
  api.exec = {};
  return api;
})();

export default CommonSnail;
