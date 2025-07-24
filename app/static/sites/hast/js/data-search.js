"use strict";

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

(function () {

  // == control variables ==
  const tmpFamilyOptions = [];
  let isLanding = true;
  const PER_PAGE = 50;

  // == init ==
  const searchContainer = document.getElementById('data-search-container');
  const filterWrapper = document.getElementById('data-search-filter-wrapper');
  const filterComponent = document.getElementById('data-search-filter');
  const resultWrapper = document.getElementById('data-search-result-wrapper');
  const toggle = document.getElementById('data-search-toggle-filter');
  const form = document.getElementById('data-search-form');
  const submitButtonTop = document.getElementById('submit-button-top');
  const submitButtonBottom = document.getElementById('submit-button-bottom');
  const clearButton = document.getElementById('clear-button');
  const closeButton = document.getElementById('close-button');

  const paginationElem = document.getElementById('pagination');
  const downloadButton = document.getElementById('download-button');

  let dataGrid = new w2grid({
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
    //async onSelect(event) {
    //  await event.complete
      //console.log('select', event.detail, this.getSelection())
      //state.selected = this.getSelection();
    //},
    onClick(event) {
      let record = this.get(event.detail.recid);
      const img = document.getElementById('record-grid-img');
      img.setAttribute('src', record.image_url);
      grid2.clear()
      let country = '';
      let adm1 = '';
      let adm2 = '';
      let adm3 = '';
      let other = [];
      record._named_areas.forEach( na => {
        if (na.area_class_id === 7) {
          country = na.display_name;
        } else if (na.area_class_id === 8) {
          adm1 = na.display_name;
        } else if (na.area_class_id === 9) {
          adm2 = na.display_name;
        } else if (na.area_class_id === 10) {
          adm3 = na.display_name;
        } else {
          other.push(na.display_name);
        }
      });
      let alt = record._altitude;
      if (record._altitude2) {
        alt = `${alt} - ${record._altitude2}`;
      }
      grid2.add([
        { recid: 0, name: '館號:', value: record.catalog_number },
        { recid: 1, name: '物種:', value: record.taxon },
        { recid: 2, name: '採集者:', value: record.collector },
        { recid: 3, name: '採集號:', value: record.field_number },
        { recid: 4, name: '採集日期:', value: record.collect_date },
        { recid: 5, name: '採集國家:', value: country },
        { recid: 6, name: '採集行政區1:', value: adm1 },
        { recid: 7, name: '採集行政區2:', value: adm2 },
        { recid: 8, name: '採集行政區3:', value: adm3 },
        { recid: 9, name: '詳細地點:', value: record._locality_text },
        { recid: 9, name: '其他地點:', value: other.join('|') },
        { recid: 10, name: '海拔:', value: alt },
        { recid: 11, name: '模式標本:', value: record.type_status },
      ])
    }
  });

  // utils
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
      .catch(error => console.log(error));
  };

  const fetchOptions = async (endpoint, filtr) => {
    const url = `${endpoint}?filter=${JSON.stringify(filtr)}&range=${JSON.stringify([0, 500])}`; // no limit
    const res = await fetchData(url);
    return res.data.map( x => ({ id: x.id, text: x.display_name }));
  };

  const resetSelect2 = (selector) => {
    $(selector).html('').val('').select2();
  };

  const renderResult = (results) => {
    document.getElementById('result-total').textContent = results.total;
    document.getElementById('result-elapsed').textContent = Number.parseFloat(results.elapsed).toFixed(2);

    dataGrid.records = results.data.map( x => {
      const loc = x.named_areas.map( x => {
        return x.display_name;
      });
      if (x.locality_text) {
        loc.push(x.locality_text);
      }
      //console.log(x);
      return {
        recid: x.unit_id,
        catalog_number: x.accession_number,
        taxon: x.taxon?.display_name,
        collector: x.collector?.display_name,
        field_number: x.field_number,
        collect_date: x.collect_date,
        locality: loc.join(' | '),
        image_url: x.image_url,
        _named_areas: x.named_areas,
        _locality_text: x.locality_text,
        _altitude: x.altitude,
        _altitude2: x.altitude2,
        _type_status: x.type_status,
      };
    });
    dataGrid.refresh();
  };

  // == Apply select2 ==
  // taxon
  $('#family-id')
    .val('')
    .select2()
    .on('change', async (e) => {
      const parentId = e.target.value;
      const data = await fetchOptions('/api/v1/taxa', {rank: 'genus', parent_id: parentId});
      $('#genus-id').html('').select2({data: data}).val('').select2();
      resetSelect2('#species-id');
    });

  $('#genus-id').on('change', async (e) => {
    const parentId = e.target.value;
    const data = await fetchOptions('/api/v1/taxa', {rank: 'species', parent_id: parentId});
    $('#species-id').html('').select2({data: data}).val('').select2();
  });

  $('#collector-id').select2({
    ajax: {
      url: '/api/v1/people',
      data: function (params) {
        if (params?.term?.length >= 1) {
          var query = {
            filter: JSON.stringify({q: params.term, is_collector: '1'}),
          };
          return query;
        }
      },
      delay: 250,
      processResults: function (data) {
        return {
            results: data.data.map( x => ({id: x.id, text: x.display_name}))
        };
      },
    }
  });

  // location
  const continentSelect = document.getElementById('continent-id');
  continentSelect.onchange = async(e) => {
    const data = await fetchOptions('/api/v1/named-areas', { area_class_id: 7, continent: e.target.value});
    $('#country-id').html('').select2({data: data}).val('').select2();
  };

  $('#country-id').select2({
    ajax: {
      url: '/api/v1/named-areas',
      data: function (params) {
        if (params?.term?.length >= 1) {
          var query = {
            filter: JSON.stringify({q: params.term, area_class_id: 7}),
          };
          return query;
        }
      },
      delay: 250,
      processResults: function (data) {
        return {
            results: data.data.map( x => ({id: x.id, text: x.display_name}))
        };
      },
    },
  }).on('change', async (e) => {
    const parentId = e.target.value;
    const data = await fetchOptions('/api/v1/named-areas', {area_class_id: 8, parent_id: parentId});
    $('#adm1-id').html('').select2({data: data}).val('').select2();
    resetSelect2('#adm2-id');
    resetSelect2('#adm3-id');
  });
  $('#adm1-id').on('change', async (e) => {
    const parentId = e.target.value;
    const data = await fetchOptions('/api/v1/named-areas', {area_class_id: 9, parent_id: parentId});
    $('#adm2-id').html('').select2({data: data}).val('').select2();
    resetSelect2('#adm3-id');
  });
  $('#adm2-id').on('change', async (e) => {
    const parentId = e.target.value;
    const data = await fetchOptions('/api/v1/named-areas', {area_class_id: 10, parent_id: parentId});
    $('#adm3-id').html('').select2({data: data}).val('').select2();
  });
  $('#named_area__park-id').select2({
    ajax: {
      url: function (params) {
        const filtr = {
          area_class_id: 5,
          q: params.term,
        };
        return `/api/v1/named-areas?filter=${JSON.stringify(filtr)}`;
      },
      data: null,
      delay: 250,
      processResults: function (data) {
        return {
            results: data.data.map( x => ({id: x.id, text: x.display_name}))
        };
      },
    },
  });
  $('#named_area__locality-id').select2({
    ajax: {
      url: function (params) {
        const filtr = {
          area_class_id: 6,
          q: params.term,
        };
        return `/api/v1/named-areas?filter=${JSON.stringify(filtr)}`;
      },
      data: null,
      delay: 250,
      processResults: function (data) {
        return {
            results: data.data.map( x => ({id: x.id, text: x.display_name}))
        };
      },
    },
  });

  const refreshPagination = (page, total, perPage) => {
    const pageList = [];
    const numPages = Math.ceil(total / perPage);

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
        const p = parseInt(e.currentTarget.dataset.page);
        Searcher.setPage(p);
        doSearch();
      };
    });
  };

  const Searcher = (function () {
    let currentFilter = {};
    let currentPage = 1;
    let currentSort = '';
    let perPage = PER_PAGE;

    function setFilter(form) {
      const formData = new FormData(form);
      //console.log('formData', formData);
      const filtr = {};

      // normalize taxon_ids
      let taxon_id = null;
      const species = formData.get('species');
      const genus = formData.get('genus');
      const family = formData.get('family');
      if (species) {
        taxon_id = species;
      } else if (genus) {
        taxon_id = genus;
      } else if (family) {
        taxon_id = family;
      }

      if (taxon_id) {
        filtr.taxon_id = taxon_id;
      }

      // normalize named_area_id
      const named_area_ids = [];
      const adm1 = formData.get('adm1');
      const adm2 = formData.get('adm2');
      const adm3 = formData.get('adm3');
      const park = formData.get('named_area__park');
      const loc = formData.get('named_area__locality');
      if (adm1) {
        named_area_ids.push(adm1);
      } else if (adm2) {
        named_area_ids.push(adm2);
      } else if (adm3) {
        named_area_ids.push(adm3);
      }
      if (park) {
        named_area_ids.push(park);
      }
      if (loc) {
        named_area_ids.push(loc);
      }

      if (named_area_ids.length) {
        filtr.named_area_id = named_area_ids;
      }

      // normalize collector_id
      let collector_id = null;
      if (formData.get('collector')) {
        filtr.collector_id = formData.get('collector');
      }
      for (const [name, value] of formData.entries()) {
        // exclude fields
        if (['species', 'genus', 'family', 'adm1', 'adm2', 'adm3', 'named_area__park', 'named_area__locality', 'collector'].indexOf(name) < 0) {
          if (value) {
            filtr[name] = value;
          }
        }
      }
      currentFilter = filtr;
      console.log('currentFilter', filtr);
    };

    async function go(downloadData){
      let payload = {};

      if (Object.keys(currentFilter).length > 0) {
        payload.filter = currentFilter;
      }

      if (downloadData === undefined) {
        if (currentSort) {
          payload.sort = [currentSort];
        }
        payload.range = [(currentPage-1) * perPage, currentPage * perPage];
      } else {
        payload.download = downloadData;
      }
      const searchList = [];
      for (const [name, value] of Object.entries(payload)) {
        searchList.push(`${name}=${JSON.stringify(value)}`);
      }
      let queryString = searchList.join('&');
      let url = `/api/v1/search?${queryString}`;
      return await fetchData(url);
    }

    function setPage (page) {
      currentPage = page;
    }

    function setSort (sort) {
      currentSort = sort;
      currentPage = 1;
    }

    function getState (param) {
      if (param === 'filter' ) {
        return currentFilter;
      } else if (param === 'page' ) {
        return currentPage;
      } else if (param === 'sort' ) {
        return currentSort;
      }
    }

    return { setFilter, setPage, setSort, getState, go };
  })();

  const goSearch = async (toPage, perPage=PER_PAGE, toSort='') => {
    console.log(toPage, perPage, toSort);
    let payload = {};
    let fromFormData = false;
    let page = null;
    if (toPage === undefined) {
      page = 1;
      currentFilter = getFilterFromFormData();
    } else {
      page = parseInt(toPage);
    }

    if (Object.keys(currentFilter).length > 0) {
      payload.filter = currentFilter;
    }
    if (toSort) {
      payload.sort = [toSort];
      page = 1;
    }
    payload.range = [(page-1) * perPage, page * perPage];

    const searchList = [];
    for (const [name, value] of Object.entries(payload)) {
      searchList.push(`${name}=${JSON.stringify(value)}`);
    }
    let queryString = searchList.join('&');
    let url = `/api/v1/search?${queryString}`;

    // render results
    if (isLanding) {
      filterWrapper.classList.remove('uk-width-1-1');
      filterWrapper.classList.add('uk-width-1-4');
      resultWrapper.classList.remove('uk-hidden');
      searchContainer.classList.remove('uk-container-small');
      closeButton.classList.remove('uk-hidden');
    } else {
      isLanding = false;
    }
    dataGrid.clear();

    const results = await fetchData(url);
    console.log('search results: ', currentFilter, results);
    renderResult(results);
    refreshPagination(page, results.total, perPage);
  };


  const doSearch = async () => {
    dataGrid.clear();

    const results = await Searcher.go();
    console.log('search results: ', results);
    renderResult(results);
    refreshPagination(Searcher.getState('page'), results.total, PER_PAGE);
  };

  downloadButton.onclick = (e) => {
    e.preventDefault();
    //Searcher.getState('filter')
    const downloadData = {
      format: 'DWC',
      downloadKey: '',
    };
    Searcher.setFilter(form);
    Searcher.go(downloadData);
  };

  const handleSubmit = () => {
    // render results
    if (isLanding) {
      filterWrapper.classList.remove('uk-width-1-1');
      filterWrapper.classList.add('uk-width-1-4');
      resultWrapper.classList.remove('uk-hidden');
      searchContainer.classList.remove('uk-container-small');
      closeButton.classList.remove('uk-hidden');
    } else {
      isLanding = false;
    }

    Searcher.setPage(1);
    Searcher.setFilter(form);

    doSearch();
  };
  submitButtonTop.onclick = (e) => {
    e.preventDefault();
    handleSubmit();
  };

  submitButtonBottom.onclick = (e) => {
    e.preventDefault();
    handleSubmit();
  };

  clearButton.onclick = (e) => {
    form.reset();
    const select2List = ['genus', 'species', 'collector', 'country', 'adm1', 'adm2', 'adm3', 'named_area__park', 'named_area__locality'];
    select2List.forEach( x => {
      resetSelect2(`#${x}-id`);
    });
    $('#family-id').val('').select2();
  };

  closeButton.onclick = (e) => {
    filterWrapper.classList.add('uk-hidden');
    toggle.classList.remove('uk-hidden');
  };

  toggle.onclick = (e) => {
    filterWrapper.classList.remove('uk-hidden');
    toggle.classList.add('uk-hidden');
  };


  const sortSelect = document.getElementById('sort-select');
  sortSelect.onchange = (e) => {
    Searcher.setSort(e.target.value);
    doSearch();
  };

  let grid2 = new w2grid({
    name: 'grid2',
    box: '#grid2',
    header: 'Details',
    show: { header: true, columnHeaders: false },
    name: 'grid2',
    columns: [
        { field: 'name', text: 'Name', size: '100px', style: 'background-color: #efefef; border-bottom: 1px solid white; padding-right: 5px;', attr: "align=right" },
        { field: 'value', text: 'Value', size: '100%' }
    ]
  });

  /*
  new TomSelect('#select-fts',{
    valueField: 'value',
    labelField: 'name',
    searchField: [],
    optgroupField: 'class',
    optgroups: [
      {value: 'taxa', label: 'Taxon', label_zh: '物種'},
      {value: 'collectors', label: 'Collector', label_zh: '採集者'},
    ],
    // fetch remote data
    load: function(query, callback) {
      let url = '/api/v1/searchbar?q=' + encodeURIComponent(query);
      fetch(url)
	.then(response => response.json())
	.then(json => {
          console.log(json);
          const options = [];
          for (const [cls, data] of Object.entries(json)) {
            for (const [_, item] of Object.entries(data)) {
              options.push({class: cls, value: item.id, name: item.display_name});
            }
          }
	  callback(options);
	}).catch(()=>{
	  callback();
	});
    },
    render: {
      optgroup_header: function(data, escape) {
	return '<div class="optgroup-header">' + escape(data.label) + ' <span class="scientific">' + escape(data.label_zh) + '</span></div>';
      }
    }
  });
  */
})();

