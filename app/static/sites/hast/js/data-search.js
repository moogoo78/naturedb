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
  let pagination = {
    page: 1,
    perPage: 50,
  };
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
    async onSelect(event) {
      await event.complete
      //console.log('select', event.detail, this.getSelection())
      //state.selected = this.getSelection();
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

  const render = (results, page) => {
    dataGrid.records = results.data.map( x => {
      const loc = x.named_areas.map( x => {
        return x.display_name;
      });
      if (x.locality_text) {
        loc.push(x.locality_text);
      }
      return {
        recid: x.item_key,
        catalog_number: x.accession_number,
        taxon: x.taxon?.display_name,
        collector: x.collector?.display_name,
        field_number: x.field_number,
        collect_date: x.collect_date,
        locality: loc.join(' | '),
      };
    });
    dataGrid.refresh();
    refreshPagination(page, results.total, pagination.perPage);
  };

  // == Apply select2 ==
  // taxon
  $('#family-id')
    .val('')
    .select2({width: '100%'})
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
        pagination.page = parseInt(e.currentTarget.dataset.page);
        doSubmit();
      };
    });
  };

  const doSubmit = async (sumbitter) => {
    const formData = new FormData(form, sumbitter);
    console.log('formData', formData);
    const filtr = {};
    const payload = {};

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
    formData.delete('species');
    formData.delete('genus');
    formData.delete('family');

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
    formData.delete('adm1');
    formData.delete('adm2');
    formData.delete('adm3');
    formData.delete('named_area__park');
    formData.delete('named_area__locality');

    for (const [name, value] of formData.entries()) {
      if (value) {
        filtr[name] = value;
      }
    }

    if (Object.keys(filtr)) {
      payload.filter = filtr;
    }
    payload.range = [(pagination.page-1)*pagination.perPage, pagination.page * pagination.perPage];
    const searchList = [];
    for (const [name, value] of Object.entries(payload)) {
      searchList.push(`${name}=${JSON.stringify(value)}`);
    }
    let queryString = searchList.join('&');
    let url = `/api/v1/search?${queryString}`;
    console.log('submit', filtr);
    console.log('search', url);

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
    console.log(results);
    render(results, pagination.page);
  };

  submitButtonTop.onclick = (e) => {
    e.preventDefault();
    doSubmit(submitButtonTop);
  };

  submitButtonBottom.onclick = (e) => {
    e.preventDefault();
    doSubmit(submitButtonBottom);
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

})();

