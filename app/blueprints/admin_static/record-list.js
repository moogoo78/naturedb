$(document).ready(function() {
  $('#form-search').select2({
    tags: true,
    multiple: true,
    minimumInputLength: 1,
    ajax: {
      url: '/admin/api/searchbar',
      delay: 250,
      data: function (params) {
        return {
          q: params.term,
        };
      },
      processResults: function (data) {
        let options = data.map( cat => {
          let children = [];
          if (cat.key === 'collector') {
            children = cat.items.map( x => {
              return {
                id: `collector_id:${x.id}`,
                text: `採集者:${x.display_name}`,
              };
            });
          } else if (cat.key === 'taxon') {
            children = cat.items.map( x => {
              return {
                id: `taxon_id:${x.id}`,
                text: `學名:${x.display_name}`,
              };
            });
          } else if (cat.key === 'field_number') {
            children = cat.items.map( x => {
              return {
                id: `record_id:${x[0]}`,
                text: `採集號:${x[1].display_name} ${x[2]}`,
              };
            });
          } else if (cat.key === 'catalog_number') {
            children = cat.items.map( x => {
              return {
                id: `record_id:${x[0]}`,
                text: `館號:${x[1]}`,
              };
            });
          }
          return {
            text: cat.label,
            children: children,
          };
        });
        return {
          results: options
        };
      }
    }
  });

  let grid = new w2grid({
    name: 'grid',
    box: '#record-grid',
    show: {
      footer: true,
      //toolbar: true,
      lineNumbers: true,
      selectColumn: true,
    },
    multiSelect: true,
    columns: GRID_COLUMNS,
    async onSelect(event) {
      await event.complete
      //console.log('select', event.detail, this.getSelection())
      state.selected = this.getSelection();
    }
  });

  let state = {
    page: 1,
    perPage: 50,
    total: 0,
    filter: {},
    selected: [],
  };


  const paginationElem = document.getElementById('pagination');
  const loading = document.getElementById('loading');

  /** makeDom by schema
   * {element(|text)(=attrs)}.{subElement}
   * attrs: foo:bar;baz
   * caution: .=:; is controled term, cannot use
   * let x = makeDom("li=class:u-active;data-key:aa;no.a|link=href:aoeu.span|text", [[0, ]])
   */
  function makeDom(schema) {
    const layers = schema.split('.');
    let currentElement = null;

    for (let i = layers.length - 1; i >= 0; i--) {
      let parsed = {
        element: layers[i],
        attrs: {},
        text: '',
      };
      if (layers[i].includes('|')) {
        const [elem, text] = layers[i].split('|');
        parsed.element = elem;
        if (text) {
          parsed.text = text;
        }
      }

      if (parsed.element.includes('=')){
        const [ele, attrs] = parsed.element.split('=');
        parsed.element = ele;
        const data = attrs.split(';');
        data.forEach( d => {
          let [k, v] = d.split(':');
          parsed.attrs[k] = v || '';
        });
      }

      const element = document.createElement(parsed.element);
      if (Object.keys(parsed.attrs)) {
        for (const [key, value] of Object.entries(parsed.attrs)) {
          element.setAttribute(key, value);
        }
        if (parsed.text) {
          element.textContent = parsed.text;
        }
      }
      if (currentElement) {
        element.appendChild(currentElement);
      }
      currentElement = element;
    }
    return currentElement;
  }

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

  const refreshPagination = (page) => {
    state.page = page;
    const pageList = [];
    const numPages = Math.ceil(state.total / state.perPage);

    if (page === 1) {
      pageList.push(makeDom('li=class:uk-disabled.a=href:#.span=uk-pagination-previous'));
    } else {
      pageList.push(makeDom(`li.a=href:#;data-page:${(page-1)}.span=uk-pagination-previous`));
    }

    if (numPages < 10) {
      for (let i=1; i <= numPages; i++) {
        if (page === i) {
          pageList.push(makeDom(`li=class:uk-active.span|${(i)}`));
        } else {
          pageList.push(makeDom(`li.a=href:#;data-page:${i}.span|${(i)}`));
        }
      }
    } else {
      if (page < 4) {
        for (let i=1; i < 4; i++) {
          if (page === i) {
            pageList.push(makeDom(`li=class:uk-active.span|${(i)}`));
          } else {
            pageList.push(makeDom(`li.a=href:#;data-page:${i}.span|${(i)}`));
          }
        }
        pageList.push(makeDom('li=class:uk-disabled.span|…'));
        pageList.push(makeDom(`li.a=href:#;data-page:${numPages}.span|${numPages}`));
      } else if (page > numPages - 3) {
        pageList.push(makeDom(`li.a=href:#;data-page:1.span|1`));
        pageList.push(makeDom('li=class:uk-disabled.span|…'));
        for (let i=numPages-3; i <= numPages; i++) {
          if (page === i) {
            pageList.push(makeDom(`li=class:uk-active.span|${(i)}`));
          } else {
            pageList.push(makeDom(`li.a=href:#;data-page:${i}.span|${(i)}`));
          }
        }
      } else {
        pageList.push(makeDom(`li.a=href:#;data-page:1.span|1`));
        pageList.push(makeDom('li=class:uk-disabled.span|…'));

        pageList.push(makeDom(`li.a=href:#;data-page:${(page-1)}.span|${(page-1)}`));
        pageList.push(makeDom(`li=class:uk-active.span|${page}`));
        pageList.push(makeDom(`li.a=href:#;data-page:${page+1}.span|${(page+1)}`));
        pageList.push(makeDom('li=class:uk-disabled.span|…'));
        pageList.push(makeDom(`li.a=href:#;data-page:${numPages}.span|${numPages}`));
      }
    }
    if (page === numPages) {
      pageList.push(makeDom('li=class:uk-disabled.a=href:#.span=uk-pagination-next'));
    } else {
      pageList.push(makeDom(`li.a=href:#;data-page:${(page+1)}.span=uk-pagination-next`));
    }

    paginationElem.replaceChildren(...pageList);
    let pageLinkList = paginationElem.querySelectorAll('a[data-page]');
    pageLinkList.forEach( x => {
      x.onclick = (e) => {
        e.preventDefault();
        //refreshPagination(parseInt(e.currentTarget.dataset.page));
        state.page = parseInt(e.currentTarget.dataset.page);
        fetchData();
      };
    });
  };

  const init = () => {
    fetchData();
  };

  const fetchData = async () => {
    loading.classList.remove('uk-hidden');
    document.getElementById('result-total').textContent = '...';
    document.getElementById('result-note').textContent = '';
    grid.clear();

    let url = '/admin/api/records';
    const payload = {
      range: [(state.page-1)*state.perPage, (state.page*state.perPage)],
    };
    //url = `${url}?range=${JSON.stringify()}`;
    if (Object.keys(state.filter).length > 0) {
      //url = `${url}&filter=${JSON.stringify(state.filter)}`;
      payload['filter'] = state.filter;
    };
    const parts = [];
    for (const [k, v] of Object.entries(payload)) {
      console.log(k, v, '====');
      parts.push(`${k}=${JSON.stringify(v)}`);
    }
    if (parts.length > 0) {
      url += '?' + parts.join('&');
    }

    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Response status: ${response.status}`);
      }
      const result = await response.json();
      console.log(result);
      loading.classList.add('uk-hidden');
      state.total = result.total;
      const start = (state.page - 1) * state.perPage + 1;
      const end = Math.min((state.page * state.perPage), state.total);
      document.getElementById('result-total').textContent = result.total.toLocaleString();
      if (state.total > 0) {
        document.getElementById('result-note').textContent = `(${start} - ${end})`;
      } else {
        document.getElementById('result-note').textContent = '';
      }

      grid.records = result.data.map( x => {
        return {
          recid: x.item_key,
          ...x,
        };
      });
      grid.refresh();
      refreshPagination(state.page);
    } catch(error) {
      console.error(error.message);
      alert('server error');
    }
  };

  const submitButton = document.getElementById('form-submit');
  submitButton.onclick = (e) => {
    e.preventDefault();
    const form = document.getElementById('form');
    const formData = new FormData(form);
    //console.log(formData);
    let filter = {};
    let qList = [];
    for (const [key, value] of formData) {
      if (value) {
        if (key === 'q') {
          qList.push(value);
        } else {
          filter[key] = value;
        }
      }
    }
    if (qList.length > 0) {
      filter['q'] = qList;
    }

    state = {
      ...state,
      filter: filter,
      page: 1,
    };
    fetchData();
  };

  let userCatList = document.querySelectorAll('.nav-user-list');
  userCatList.forEach( x => {
    x.onclick = (e) => {
      e.preventDefault();
      const d = e.target.dataset;
      //, state.selected);
      let payload = {
        entity_id: state.selected,
        uid: d.uid,
        category_id: d.cat,
      };
      UIkit.dropdown('#user-list-dropdown').hide(0);
      postData(`/admin/api/user-list`, payload)
        .then( resp => {
          // render alert
          UIkit.notification({message:`${resp.message}: ${resp.content}`});
        });
    };
  });
  init();
});
