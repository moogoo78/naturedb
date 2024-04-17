(function() {
  "use strict";

  // utils
  const postData = (endpoint, data) => {
  const headers = {
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    'X-Requested-With': 'XMLHttpRequest'
  };
  return fetch(endpoint, {
    method: "POST",
    cache: "no-cache",
    credentials: "same-origin",
    headers: headers,
    body: JSON.stringify(data),
  })
    .then(response => response.json())
    .then(json => {
      return Promise.resolve(json);
    })
    .catch(error => console.log(error));
  };

  const chkList = document.getElementsByClassName('add-to-list');
  const alertContainer = document.getElementById('alert-container');

  for (const chk of chkList) {
    chk.onclick = (e) => {
      e.preventDefault();
      const d = e.currentTarget.dataset;
      const label = e.currentTarget.innerHTML;
      let data = {
        entity_id: d.entity_id,
        uid: d.uid,
        category_id: d.list_category,
      }

      UIkit.dropdown(`#record-list-dropdown-${d.entity_id}`).hide(0);
      postData(`/admin/api/user-list`, data)
        .then( resp => {
          //console.log(resp);
          // change icon
          const container = document.getElementById(`user-list-labels-container-${d.entity_id}`);
          if (resp.code === 'added') {
            const span = document.createElement('span');
            span.classList.add('uk-badge');
            span.textContent = label;
            container.appendChild(span);
            //container.appendChild(document.createTextNode('\u00A0')); // HACK
          }

          // render alert
          UIkit.notification({message:`${resp.message}: ${resp.entity_id}`});
        })
    }
  }
})();
