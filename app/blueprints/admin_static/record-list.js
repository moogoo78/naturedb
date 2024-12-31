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
  const chkListCat = document.getElementsByClassName('add-to-list-category');
  const alertContainer = document.getElementById('alert-container');
  //const searchInput = document.getElementById('ndb-record-search-input');

  let chipBox = (function () {
    /**
       chip:
         - key
         - value
         - label
         - displayValue
       }
    */
    const chipCategories = [['collectors', '採集者'], ['taxa', '學名']];

    let chipInput = document.getElementById('ndb-chipbox-input');
    let chipDropdown = document.getElementById('ndb-chipbox-dropdown');
    let chipDropdownItems = document.getElementById('ndb-chipbox-dropdown-item-container');
    let chips = document.getElementById('ndb-chipbox-chip-wrapper');
    let submit = document.getElementById('ndb-chipbox-submit');
    let reset = document.getElementById('ndb-chipbox-reset');
    let currentChips = [];


    let render = () => {
      chips.innerHTML = '';
      currentChips.forEach( chip => {
        let chipElem = document.createElement('div');
        chipElem.classList.add('ndb-chipbox-chip');
        chipElem.innerHTML = `${chip.label}: ${chip.displayValue}`;
        chips.appendChild(chipElem);
      });
    };
    let addChip = (chip) => {
      currentChips.push(chip);
      render();
    };

    let handleSubmit = (e) => {
      e.preventDefault();
      //console.log(currentChips);
      let payload = {};
      if (chipInput.value) {
        payload.q = chipInput.value;
      }
      if (currentChips.length > 0) {
        currentChips.forEach( chip => {
          if (!payload.hasOwnProperty(chip.key)) {
            payload[chip.key] = [];
          }
          payload[chip.key].push(chip.value);
        });
      }
      const searchParams = new URLSearchParams(payload);
      const url = `/admin/records?${searchParams.toString()}`;
      location.replace(url);
    };
    let handleReset = (e) => {
      e.preventDefault();
      currentChips = [];
      chipDropdown.style.display = 'none';
      chipInput.value = '';
      chips.innerHTML = '';
    };
    let handleInput = (e) => {
      const q = e.target.value;
      if (q.length > 0) {
        // TODO: promise.all() ?
        //const endpoint = `/api/v1/people?filter={"is_collector":"1","q":"${q}"}&sort=[{"name":""}]`;
        const endpoint = `/api/v1/searchbar?q=${q}`;
        fetch(endpoint)
          .then(resp => resp.json())
          .then(results => {
            let total = 0;
            chipCategories.forEach( cat => {
              total += results[cat[0]].length;
            });

            chipDropdownItems.innerHTML = '';
            chipDropdown.style.display = 'block';
            chipCategories.forEach( cat => {
              let liCat = document.createElement('li');
              liCat.classList.add('uk-nav-header');
              liCat.innerHTML = cat[1];
              chipDropdownItems.appendChild(liCat);
              results[cat[0]].forEach( item => {
                let li = document.createElement('li');
                let a = document.createElement('a');
                a.href = '#';
                a.dataset.value = item.id;
                a.onclick = (e) => {
                  chipBox.addChip({
                    key: cat[0],
                    value: item.id,
                    label: cat[1],
                    displayValue: item.display_name,
                  });
                  chipDropdown.style.display = 'none';
                  chipDropdownItems.innerHTML = '';
                  chipInput.value = '';
                };
                a.innerHTML = item.display_name;
                li.appendChild(a);
                chipDropdownItems.appendChild(li);
              });
            });
            if (total <= 0) {
              chipDropdown.style.display = 'none';
            }
          })
          .catch(error => alert(error));
      }
    };
    submit.addEventListener('click', handleSubmit);
    reset.addEventListener('click', handleReset);
    chipInput.addEventListener('input', handleInput);

    // init
    let init = async () => {

      let entryUrl = new URL(location);
      const searchParams = new URLSearchParams(entryUrl.search);
      let urls = [];
      if (searchParams.has('q')) {
        chipInput.value = searchParams.get('q');
      }
      if (searchParams.has('collectors')) {
        searchParams.get('collectors').split(',').forEach( x => {
          urls.push([{key: 'collectors', value: x, label: '採集者'}, `/api/v1/people/${x}`]);
        });
      }
      if (searchParams.has('taxa')) {
        searchParams.get('taxa').split(',').forEach( x => {
          urls.push([{key: 'taxa', value: x, label: '學名'}, `/api/v1/taxa/${x}`]);
        });
      }
      const results = await Promise.all(urls.map(async ([data, url]) => {
        return fetch(url)
          .then( resp => resp.json())
          .then( results => {
            return {
              ...data,
              displayValue: results.display_name,
            };
          });
      }));
      //console.log(results);
      results.forEach( r => { addChip(r);});
    };
    init();

    return {
      addChip: addChip,
      render: render,
    };
  })();


  for (const chk of chkList) {
    chk.onclick = (e) => {
      e.preventDefault();
      const d = e.currentTarget.dataset;
      const label = e.currentTarget.innerHTML;
      let data = {
        entity_id: d.entity_id,
        uid: d.uid,
        category_id: d.list_category,
      };

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
        });
    };
  }

  for (const chk of chkListCat) {
    chk.onclick = (e) => {
      e.preventDefault();
      const d = e.currentTarget.dataset;
      const label = e.currentTarget.innerHTML;

      let entryUrl = new URL(location);
      let searchParams = new URLSearchParams(entryUrl.search);
      let data = {
        uid: d.uid,
        category_id: d.list_category,
        query: searchParams.toString(),
      };

      UIkit.dropdown('#ndb-user-list-cat').hide(0);

      postData(`/admin/api/user-list`, data)
        .then( resp => {
          //console.log(resp);
          // render alert
          UIkit.notification({message: `${resp.message}: ${d.list_category_name}`});
        });
    };
  }
})();

$(document).ready(function() {
  $('#record-group').select2();
});
