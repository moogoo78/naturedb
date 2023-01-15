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

  const chkList = document.getElementsByClassName('favorite-checkbox');
  const alertContainer = document.getElementById('alert-container');

  for (const chk of chkList) {
    chk.onclick = (e) => {
      e.preventDefault();
      let data = {
        entity_id: e.currentTarget.dataset.entity_id,
        uid: e.currentTarget.dataset.uid,
      }
      postData('/api/v1/favorites', data)
        .then( resp => {
          // change icon
          const chk = document.getElementById(`checkbox-${data.entity_id}`);
          chk.setAttribute('uk-icon', (resp.action === 'add') ? 'heart' : 'minus');

          // render alert
          const action = (resp.action === 'add') ? '新增' : '刪除';
          UIkit.notification({message: `我的最愛: ${action} ${resp.entity_id}`});

          /* const alert = document.createElement('div');
           * alert.setAttribute('uk-alert', '');
           * const style = (resp.action === 'add') ? 'success' : 'danger';
           * const action = (resp.action === 'add') ? '新增' : '刪除';
           * alert.classList.add(`uk-alert-${style}`);
           * const closeLink = document.createElement('a');
           * const content = document.createElement('p');
           * content.innerHTML = `我的最愛: ${action} ${resp.record}`;
           * closeLink.classList.add('uk-alert-close');
           * closeLink.setAttribute('uk-close', '');
           * alert.appendChild(closeLink);
           * alert.appendChild(content)
           * alertContainer.appendChild(alert); */
        })
    }
  }
})();
