// Coordinate conversion functions
const convertDDToDMS = (dd) => {
  /* arguments: decimal degree */
  const direction = (parseFloat(dd) >= 0) ? 1 : -1;
  const ddFloat = Math.abs(parseFloat(dd));
  const degree = Math.floor(ddFloat);
  const minuteFloat = (ddFloat - degree) * 60;
  const minute = Math.floor(minuteFloat);
  const secondFloat = ((minuteFloat - minute) * 60);
  const second = parseFloat(secondFloat.toFixed(4));
  return [direction, degree, minute, second];
};

const convertDMSToDD = (ddms) => {
  /* arguments: [direction, degree, minute, second] */
  return ddms[0] * (parseFloat(ddms[1]) + parseFloat(ddms[2]) / 60 + parseFloat(ddms[3]) / 3600);
};

const parseDMSString = (dmsStr) => {
  /* Parse DMS string format: "120-58-55.29" to [direction, degree, minute, second]
   * Assumes positive (East/North) direction
   */
  if (!dmsStr || dmsStr.trim() === '') return null;

  const parts = dmsStr.trim().split('-');
  if (parts.length !== 3) return null;

  const degree = parseFloat(parts[0]);
  const minute = parseFloat(parts[1]);
  const second = parseFloat(parts[2]);

  if (isNaN(degree) || isNaN(minute) || isNaN(second)) return null;

  const direction = degree >= 0 ? 1 : -1;
  return [direction, Math.abs(degree), minute, second];
};

const formatDMSString = (dmsArray) => {
  /* Format [direction, degree, minute, second] to "D-M-S.SS" string */
  if (!dmsArray || dmsArray.length !== 4) return '';
  const [direction, degree, minute, second] = dmsArray;
  const signedDegree = direction * degree;
  return `${signedDegree}-${minute}-${second.toFixed(2)}`;
};

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
    sort: [],
    selected: [],
  };


  const paginationElem = document.getElementById('pagination');
  const loading = document.getElementById('loading');
  const quickEditBtn = document.getElementById('quick-edit-btn');

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

  let currentIndex = 0;
  
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

  const toPageSelect = document.getElementById('to-page-select');
  const refreshPagination = (page) => {
    state.page = page;
    const pageList = [];
    const numPages = Math.ceil(state.total / state.perPage);

    toPageSelect.innerHTML = '';
    for(let i=0; i<numPages; i++) {
      if (i+1 === page) {
        toPageSelect[i] = new Option(String(i+1), toPageSelect.length, true, true);
      } else {
        toPageSelect[i] = new Option(String(i+1), toPageSelect.length, false, false);
      }
    }
    $('#to-page-select').select2();
    toPageSelect.onchange = (e) => {
      e.preventDefault();
      refreshPagination(parseInt(e.target.value) + 1);
      fetchData();
    };

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

  const renderTranscriptionView = (records) => {

    /*
    let grid2 = new w2grid({
      name: 'grid2',
      box: '#grid2',
      columns: [
        GRID_COLUMNS[0],
        GRID_COLUMNS[1],
      ],
      records: records,
      onClick(event) {
        let record = this.get(event.detail.recid)
        console.log(record);
        let img = document.getElementById('grid2-detail-img');
        img.src = record.image_url.replace('-s.jpg', '-l.jpg');
      }
    });
    */
    let thumbNav = document.getElementById('thumbnav');
    thumbNav.innerHTML = '';
    records.forEach( (v, i) => {
      let li = document.createElement('li');
      if (i === 0) {
        li.classList.add('uk-active');
      }
      let box = document.createElement('div');
      box.dataset.recindex = i;
      box.setAttribute('uk-toggle', 'target: #toggle-image');
      let img = document.createElement('img');
      img.src = v.image_url;
      img.width = '50';
      let catalogNumber = makeDom(`div|${v.catalog_number}`);

      box.appendChild(img);
      box.appendChild(catalogNumber);
      li.appendChild(box);
      box.onclick = (e) => {
        //let formCatalogNumber = document.getElementById('form-catalog-number');
        //let modalImage = document.getElementById('modal-image');
        let toggleImage = document.getElementById('toggle-image');
        toggleImage.src = records[e.target.dataset.recindex]['image_url'].replace('-s.jpg', '-x.jpg');
        //modalImage.src = records[e.target.dataset.recindex]['image_url'].replace('-s.jpg', '-o.jpg');
        //formCatalogNumber.value = records[e.target.dataset.recindex]['catalog_number'];
        
      };
      thumbNav.appendChild(li);
    });

  }; // end of renderTranscriptionView

  const init = () => {
    fetchData();

    let recordGrid = document.getElementById('record-grid'); // tab1
    //let tab2 = document.getElementById('tab2');
    /*
    new w2tabs({
    box: '#tabs',
    name: 'tabs',
    active: 'tab1',
    tabs: [
        { id: 'tab1', text: 'List' },
        { id: 'tab2', text: 'Transcription View' },
    ],
      onClick(event) {
        if (event.target === 'tab2') {
          recordGrid.classList.add('uk-hidden');
          tab2.classList.remove('uk-hidden');
        } else if (event.target === 'tab1') {
          recordGrid.classList.remove('uk-hidden');
          tab2.classList.add('uk-hidden');
        }
      }
      }); // end of w2tabs
    */
  }; // end of init

  const fetchData = async () => {
    loading.classList.remove('uk-hidden');
    quickEditBtn.classList.add('uk-hidden');
    currentIndex = 0;
    document.getElementById('result-total').textContent = '...';
    document.getElementById('result-note').textContent = '';
    grid.clear();

    let url = '/admin/api/records';
    const payload = {
      range: [(state.page-1)*state.perPage, (state.page*state.perPage)],
    };

    if (Object.keys(state.filter).length > 0) {
      payload['filter'] = state.filter;
      globalFetchArgs.filtr = payload['filter'];
    };
    if (state.sort && state.sort.length > 0) {
      payload['sort'] = state.sort;
      globalFetchArgs.sort = payload['sort'];
    };
    const parts = [];
    for (const [k, v] of Object.entries(payload)) {
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
      globalFetchArgs.begin = (state.page - 1) * state.perPage + 1;
      document.getElementById('result-total').textContent = result.total.toLocaleString();
      if (state.total > 0) {
        document.getElementById('result-note').textContent = `(${start} - ${end})`;
      } else {
        document.getElementById('result-note').textContent = '';
      }

      grid.records = result.data.map( x => {
        //console.log(x.item_key, x);
        if (!x.collector && x.verbatim_collector) {
          x.collector = `!${x.verbatim_collector}`;
        }
        if (!x.collect_date && x.verbatim_collect_date) {
          x.collect_date = `!${x.verbatim_collect_date}`;
        }
        let tlist = [];
        if (!x.taxon && x.quick__verbatim_scientific_name) {
          tlist.push(`!${x.quick__verbatim_scientific_name}`);
        }
        if (!x.taxon && x.quick__scientific_name) {
          tlist.push(`=> ${x.quick__scientific_name}`);
        }
        if (tlist.length > 0) {
          x.taxon = tlist.join(' | ');
        }
        let catalog_number = x.catalog_number;
        if (x.collection_id === 'u5') {
          // HACK: PPI
          if (x.quick__ppi_is_transcribed) {
            x.catalog_number_display = `🟢 ${catalog_number}`;
          } else {
            x.catalog_number_display = `🔴 ${catalog_number}`;
          }
        } else {
          x.catalog_number_display = catalog_number;
        }
        return {
          recid: x.item_key,
          ...x,
        };
      });
      grid.refresh();
      refreshPagination(state.page);

      // also renderTranscriptionView
      //renderTranscriptionView(w2ui.grid.records);
      if (w2ui.grid.records.length > 0) {
        refreshViewer(0);
      }
      quickEditBtn.classList.remove('uk-hidden');
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
    let sort = [];
    let qList = [];
    for (const [key, value] of formData) {
      if (value) {
        if (key === 'q') {
          qList.push(value);
        } else if (key === 'sort') {
          sort.push(value);
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
      sort: sort,
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

  // quick edit
  let currentSize = 'l';
  let imageDisplay = document.getElementById('image-display');
  let imageIndex = document.getElementById('image-viewer-index');
  let btnNext = document.getElementById('btn-viewer-next');
  let btnPrev = document.getElementById('btn-viewer-prev');
  let btnSizeL = document.getElementById('btn-viewer-size-l');
  let btnSizeX = document.getElementById('btn-viewer-size-x');
  let btnSizeO = document.getElementById('btn-viewer-size-o');
  let btnSubmit = document.getElementById('btn-quick-submit');

  /*
  // Initialize TomSelect for quick edit collector field
  let quickCollectorSelect = new TomSelect('#quick-collector_id', {
    valueField: 'id',
    labelField: 'display_name',
    searchField: 'display_name',
    maxItems: 1,
    load: function(query, callback) {
      if (!query.length) return callback();
      fetch(`/api/v1/people?filter=${JSON.stringify({q: query, is_collector: 1})}`)
        .then(response => response.json())
        .then(json => {
          callback(json);
        })
        .catch(err => {
          callback();
        });
    }
  });

  // Initialize TomSelect for quick edit taxon field
  let quickTaxonSelect = new TomSelect('#quick-taxon_id', {
    valueField: 'id',
    labelField: 'display_name',
    searchField: 'display_name',
    maxItems: 1,
    load: function(query, callback) {
      if (!query.length) return callback();
      fetch(`/api/v1/taxa?filter=${JSON.stringify({q: query})}`)
        .then(response => response.json())
        .then(json => {
          callback(json);
        })
        .catch(err => {
          callback();
        });
    }
  });

  // Initialize TomSelect for named_area fields with cascading filters
  let quickCountrySelect = new TomSelect('#quick-named_area_country', {
    valueField: 'id',
    labelField: 'display_name',
    searchField: 'display_name',
    maxItems: 1,
    load: function(query, callback) {
      if (!query.length) return callback();
      fetch(`/api/v1/named-areas?filter=${JSON.stringify({q: query, area_class_id: 7})}`)
        .then(response => response.json())
        .then(json => {
          callback(json);
        })
        .catch(err => {
          callback();
        });
    },
    onChange: function(value) {
      // When country changes, clear and reset ADM1, ADM2, ADM3
      quickAdm1Select.clear();
      quickAdm1Select.clearOptions();
      quickAdm2Select.clear();
      quickAdm2Select.clearOptions();
      quickAdm3Select.clear();
      quickAdm3Select.clearOptions();

      // Auto-load ADM1 options when country is selected
      if (value) {
        fetch(`/api/v1/named-areas?filter=${JSON.stringify({area_class_id: 8, parent_id: value})}`)
          .then(response => response.json())
          .then(json => {
            if (json.data && Array.isArray(json.data)) {
              json.data.forEach(option => {
                quickAdm1Select.addOption(option);
              });
            }
          })
          .catch(err => {
            console.error('Error loading ADM1 options:', err);
          });
      }
    }
  });

  let quickAdm1Select = new TomSelect('#quick-named_area_adm1', {
    valueField: 'id',
    labelField: 'display_name',
    searchField: 'display_name',
    maxItems: 1,
    load: function(query, callback) {
      if (!query.length) return callback();
      const countryId = quickCountrySelect.getValue();
      const filter = {q: query, area_class_id: 8};
      if (countryId) {
        filter.parent_id = countryId;
      }
      fetch(`/api/v1/named-areas?filter=${JSON.stringify(filter)}`)
        .then(response => response.json())
        .then(json => {
          callback(json);
        })
        .catch(err => {
          callback();
        });
    },
    onChange: function(value) {
      // When ADM1 changes, clear ADM2 and ADM3
      quickAdm2Select.clear();
      quickAdm2Select.clearOptions();
      quickAdm3Select.clear();
      quickAdm3Select.clearOptions();

      // Auto-load ADM2 options when ADM1 is selected
      if (value) {
        fetch(`/api/v1/named-areas?filter=${JSON.stringify({area_class_id: 9, parent_id: value})}`)
          .then(response => response.json())
          .then(json => {
            if (json.data && Array.isArray(json.data)) {
              json.data.forEach(option => {
                quickAdm2Select.addOption(option);
              });
            }
          })
          .catch(err => {
            console.error('Error loading ADM2 options:', err);
          });
      }
    }
  });

  let quickAdm2Select = new TomSelect('#quick-named_area_adm2', {
    valueField: 'id',
    labelField: 'display_name',
    searchField: 'display_name',
    maxItems: 1,
    load: function(query, callback) {
      if (!query.length) return callback();
      const adm1Id = quickAdm1Select.getValue();
      const filter = {q: query, area_class_id: 9};
      if (adm1Id) {
        filter.parent_id = adm1Id;
      }
      fetch(`/api/v1/named-areas?filter=${JSON.stringify(filter)}`)
        .then(response => response.json())
        .then(json => {
          callback(json);
        })
        .catch(err => {
          callback();
        });
    },
    onChange: function(value) {
      // When ADM2 changes, clear ADM3
      quickAdm3Select.clear();
      quickAdm3Select.clearOptions();

      // Auto-load ADM3 options when ADM2 is selected
      if (value) {
        fetch(`/api/v1/named-areas?filter=${JSON.stringify({area_class_id: 10, parent_id: value})}`)
          .then(response => response.json())
          .then(json => {
            if (json.data && Array.isArray(json.data)) {
              json.data.forEach(option => {
                quickAdm3Select.addOption(option);
              });
            }
          })
          .catch(err => {
            console.error('Error loading ADM3 options:', err);
          });
      }
    }
  });

  let quickAdm3Select = new TomSelect('#quick-named_area_adm3', {
    valueField: 'id',
    labelField: 'display_name',
    searchField: 'display_name',
    maxItems: 1,
    load: function(query, callback) {
      if (!query.length) return callback();
      const adm2Id = quickAdm2Select.getValue();
      const filter = {q: query, area_class_id: 10};
      if (adm2Id) {
        filter.parent_id = adm2Id;
      }
      fetch(`/api/v1/named-areas?filter=${JSON.stringify(filter)}`)
        .then(response => response.json())
        .then(json => {
          callback(json);
        })
        .catch(err => {
          callback();
        });
    }
  });
  */
  // Auto-convert DMS coordinates to decimal degrees
  const quickLongitudeInput = document.getElementById('quick-quick__longitude');
  const quickLatitudeInput = document.getElementById('quick-quick__latitude');
  const decimalLongitudeInput = document.getElementById('quick-decimal_longitude');
  const decimalLatitudeInput = document.getElementById('quick-decimal_latitude');

  // Find named areas by coordinates button
  const btnFindAreasByCoords = document.getElementById('btn-find-areas-by-coords');
  if (btnFindAreasByCoords) {
    btnFindAreasByCoords.addEventListener('click', function() {
      const longitude = parseFloat(decimalLongitudeInput.value);
      const latitude = parseFloat(decimalLatitudeInput.value);

      if (isNaN(longitude) || isNaN(latitude)) {
        UIkit.notification({message: '請先輸入經緯度座標', status: 'warning'});
        return;
      }

      // Show loading state
      this.disabled = true;
      this.textContent = '⏳';

      const filter = {
        area_class_id: [7, 8, 9, 10], // Country, ADM1, ADM2, ADM3
        within: {
          point: [longitude, latitude],
          srid: 4326
        }
      };

      fetch(`/api/v1/named-areas?filter=${JSON.stringify(filter)}`)
        .then(response => response.json())
        .then(json => {
          if (json.data && Array.isArray(json.data)) {
            // Group results by area_class_id
            const areasByClass = {
              7: null,  // COUNTRY
              8: null,  // ADM1
              9: null,  // ADM2
              10: null  // ADM3
            };

            json.data.forEach(area => {
              if (area.area_class_id && !areasByClass[area.area_class_id]) {
                areasByClass[area.area_class_id] = area;
              }
            });

            // Populate selects
            // Country
            if (areasByClass[7]) {
              quickCountrySelect.addOption(areasByClass[7]);
              quickCountrySelect.setValue(areasByClass[7].id);
            }

            // ADM1
            if (areasByClass[8]) {
              quickAdm1Select.addOption(areasByClass[8]);
              quickAdm1Select.setValue(areasByClass[8].id);
            }

            // ADM2
            if (areasByClass[9]) {
              quickAdm2Select.addOption(areasByClass[9]);
              quickAdm2Select.setValue(areasByClass[9].id);
            }

            // ADM3
            if (areasByClass[10]) {
              quickAdm3Select.addOption(areasByClass[10]);
              quickAdm3Select.setValue(areasByClass[10].id);
            }

            const foundCount = Object.values(areasByClass).filter(a => a !== null).length;
            if (foundCount > 0) {
              UIkit.notification({message: `找到 ${foundCount} 個行政區`, status: 'success'});
            } else {
              UIkit.notification({message: '此座標未找到行政區', status: 'warning'});
            }
          } else {
            UIkit.notification({message: '未找到行政區', status: 'warning'});
          }
        })
        .catch(err => {
          console.error('Error finding areas by coords:', err);
          UIkit.notification({message: '查詢失敗', status: 'danger'});
        })
        .finally(() => {
          // Reset button state
          this.disabled = false;
          this.textContent = '🌍';
        });
    });
  }

  // DMS to Decimal conversion
  if (quickLongitudeInput) {
    quickLongitudeInput.addEventListener('blur', function() {
      const dmsArray = parseDMSString(this.value);
      if (dmsArray && decimalLongitudeInput) {
        const dd = convertDMSToDD(dmsArray);
        decimalLongitudeInput.value = dd.toFixed(6);
      }
    });
  }

  if (quickLatitudeInput) {
    quickLatitudeInput.addEventListener('blur', function() {
      const dmsArray = parseDMSString(this.value);
      if (dmsArray && decimalLatitudeInput) {
        const dd = convertDMSToDD(dmsArray);
        decimalLatitudeInput.value = dd.toFixed(6);
      }
    });
  }

  // Decimal to DMS conversion (reverse)
  if (decimalLongitudeInput) {
    decimalLongitudeInput.addEventListener('blur', function() {
      const dd = parseFloat(this.value);
      if (!isNaN(dd) && quickLongitudeInput) {
        const dmsArray = convertDDToDMS(dd);
        quickLongitudeInput.value = formatDMSString(dmsArray);
      }
    });
  }

  if (decimalLatitudeInput) {
    decimalLatitudeInput.addEventListener('blur', function() {
      const dd = parseFloat(this.value);
      if (!isNaN(dd) && quickLatitudeInput) {
        const dmsArray = convertDDToDMS(dd);
        quickLatitudeInput.value = formatDMSString(dmsArray);
      }
    });
  }

  btnSubmit.onclick = (e) => {
    e.preventDefault();
    let quickForm = document.getElementById('quick-form');
    const formData = new FormData(quickForm);
    let payload = {
      item_key: w2ui.grid.records[currentIndex].item_key,
      collection_id: w2ui.grid.records[currentIndex].collection_id,
    };
    for (const [key, value] of formData) {
      payload[key] = value;
    }
    //console.log(currentIndex);
    console.log('post!!', w2ui.grid.records[currentIndex]);
    postData(`/admin/api/quick-edit`, payload)
      .then( resp => {
        // render alert
        console.log('quick save', resp);
        UIkit.notification({message:`${resp.message}: ${resp.content}`});
      });
  };

  const sizeBtnMap = {
    active: 'bg-white hover:bg-gray-100 text-gray-800 font-bold py-2 px-4 border border-gray-400 rounded shadow',
    normal: 'bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded-l" id="btn-viewer-size-l'
  };

  btnSizeL.onclick = (e) => {
    currentSize = 'l';
    refreshViewer(currentIndex);

    btnSizeL.className = sizeBtnMap['active'];
    btnSizeX.className = sizeBtnMap['normal'];
    btnSizeO.className = sizeBtnMap['normal'];
  };
  btnSizeX.onclick = (e) => {
    currentSize = 'x';
    refreshViewer(currentIndex);
    btnSizeL.className = sizeBtnMap['normal'];
    btnSizeX.className = sizeBtnMap['active'];
    btnSizeO.className = sizeBtnMap['normal'];
  };
  btnSizeO.onclick = (e) => {
    currentSize = 'o';
    refreshViewer(currentIndex);
    btnSizeL.className = sizeBtnMap['normal'];
    btnSizeX.className = sizeBtnMap['normal'];
    btnSizeO.className = sizeBtnMap['active'];
  };
  function refreshViewer(idx) {
      const recValueMap = {
        catalog_number: 'catalog_number',
        verbatim_collector: 'verbatim_collector',
        companion_text: 'companion_text',
        field_number: 'field_number',
        collect_date: 'collect_date',
        verbatim_collect_date: 'verbatim_collect_date',
        quick__scientific_name: 'quick__scientific_name',
        quick__verbatim_scientific_name: 'quick__verbatim_scientific_name',
        verbatim_locality: 'verbatim_locality',
        quick__other_text_on_label: 'quick__other_text_on_label',
        quick__user_note: 'quick__user_note',
        altitude: 'altitude',
        altitude2: 'altitude2',
        verbatim_latitude: 'verbatim_latitude',
        verbatim_longitude: 'verbatim_longitude',
        quick__longitude: 'quick__longitude',
        quick__latitude: 'quick__latitude',
        decimal_longitude: 'longitude_decimal',
        decimal_latitude: 'latitude_decimal',
        quick__id1_id: 'quick__id1_id',
        quick__id1_verbatim_identifier: 'quick__id1_verbatim_identifier',
        quick__id1_verbatim_date: 'quick__id1_verbatim_date',
        quick__id1_verbatim_identification: 'quick__id1_verbatim_identification',
        quick__id2_id: 'quick__id2_id',
        quick__id2_verbatim_identifier: 'quick__id2_verbatim_identifier',
        quick__id2_verbatim_date: 'quick__id2_verbatim_date',
        quick__id2_verbatim_identification: 'quick__id2_verbatim_identification',
      };
    imageDisplay.src = w2ui.grid.records[idx].image_url.replace('-s.jpg', `-${currentSize}.jpg`);
    imageIndex.textContent = `${idx+1}/${w2ui.grid.records.length}`;

    for (const [key, value] of Object.entries(recValueMap)) {
      let elem = document.getElementById(`quick-${key}`);
      const fieldValue = w2ui.grid.records[idx][value];
      elem.value = (fieldValue !== undefined && fieldValue !== null) ? fieldValue : '';
    }

    // Handle TomSelect collector field
    const record = w2ui.grid.records[idx];
    /*
    if (record.collector_id) {
      // Add option if it doesn't exist, then set value
      const collectorOption = {
        id: record.collector_id,
        display_name: record.collector || 'Unknown'
      };
      quickCollectorSelect.addOption(collectorOption);
      quickCollectorSelect.setValue(record.collector_id);
    } else {
      quickCollectorSelect.clear();
    }
    
    // Handle TomSelect taxon field
    if (record.proxy_taxon_id) {
      const taxonOption = {
        id: record.proxy_taxon_id,
        display_name: record.proxy_taxon_scientific_name || record.taxon || 'Unknown'
      };
      quickTaxonSelect.addOption(taxonOption);
      quickTaxonSelect.setValue(record.proxy_taxon_id);
    } else {
      quickTaxonSelect.clear();
    }

    // Handle TomSelect named_area fields
    if (record.named_areas) {
      // Country (area_class_id: 7)
      if (record.named_areas.COUNTRY) {
        quickCountrySelect.addOption({
          id: record.named_areas.COUNTRY.id,
          name: record.named_areas.COUNTRY.name
        });
        quickCountrySelect.setValue(record.named_areas.COUNTRY.id);
      } else {
        quickCountrySelect.clear();
      }

      // ADM1 (area_class_id: 8)
      if (record.named_areas.ADM1) {
        quickAdm1Select.addOption({
          id: record.named_areas.ADM1.id,
          name: record.named_areas.ADM1.name
        });
        quickAdm1Select.setValue(record.named_areas.ADM1.id);
      } else {
        quickAdm1Select.clear();
      }

      // ADM2 (area_class_id: 9)
      if (record.named_areas.ADM2) {
        quickAdm2Select.addOption({
          id: record.named_areas.ADM2.id,
          name: record.named_areas.ADM2.name
        });
        quickAdm2Select.setValue(record.named_areas.ADM2.id);
      } else {
        quickAdm2Select.clear();
      }

      // ADM3 (area_class_id: 10)
      if (record.named_areas.ADM3) {
        quickAdm3Select.addOption({
          id: record.named_areas.ADM3.id,
          name: record.named_areas.ADM3.name
        });
        quickAdm3Select.setValue(record.named_areas.ADM3.id);
      } else {
        quickAdm3Select.clear();
      }
    } else {
      // Clear all if no named_areas
      quickCountrySelect.clear();
      quickAdm1Select.clear();
      quickAdm2Select.clear();
      quickAdm3Select.clear();
      }
      */
  }

  btnNext.onclick = (e) => {
    if (currentIndex < w2ui.grid.records.length -1) {
      currentIndex += 1;
      btnNext.classList.remove('cursor-not-allowed');
      refreshViewer(currentIndex);
    } else {
      btnNext.classList.add('cursor-not-allowed');
    }
  };
  btnPrev.onclick = (e) => {
    if (currentIndex > 0) {
      currentIndex -= 1;
      btnPrev.classList.remove('cursor-not-allowed');
      refreshViewer(currentIndex);
    } else {
      btnPrev.classList.add('cursor-not-allowed');
    }
  };


  function isFormElement(element) {
    const formTags = ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'];
    return formTags.includes(element.tagName) ||
      element.contentEditable === 'true' ||
      element.isContentEditable;
}

  document.addEventListener('keydown', function(event) {
    if (isFormElement(document.activeElement)) {
      return; // Use default behavior for form elements
    }
    // Custom behavior for non-form elements
    if (event.keyCode == 39) {
      if (currentIndex < w2ui.grid.records.length -1) {
        currentIndex += 1;
        btnNext.classList.remove('cursor-not-allowed');
        refreshViewer(currentIndex);
      } else {
        btnNext.classList.add('cursor-not-allowed');
      }
    }
    else if (event.keyCode == 37) {
      if (currentIndex > 0) {
        currentIndex -= 1;
        btnPrev.classList.remove('cursor-not-allowed');
        refreshViewer(currentIndex);
      } else {
        btnPrev.classList.add('cursor-not-allowed');
      }
    }
  });
});
