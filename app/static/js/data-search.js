import Formant from './formant.js';
import { ResultView } from './search-helper-results.js';
import {default as o_} from './common-snail.js';

(function() {
  "use strict";

  // helpers
  //const $create = (tag) => { return document.createElement(tag); }
  o_.exec =  {
    show: (id) => { document.getElementById(id).removeAttribute('hidden'); },
    hide: (id) => { document.getElementById(id).setAttribute('hidden', ''); },
  };

  // elements
  const searchbarInput = o_.find('#data-search-searchbar-input');
  const searchbarDropdown = o_.find('#data-search-searchbar-dropdown');
  const searchbarDropdownList = o_.find('#data-search-searchbar-dropdown-list');
  const sortItems = o_.find('.sort-nav');
  const sortLabel = o_.find('#sort-label');

  // global state
  // const state = {
  //   results: {},
  //   resultsView: 'table',
  //   resultsChecklist: {},
  //   resultsMap: {},
  //   map: null,
  //   mapMarkers: [],
  // };
  let searchSort = {'field_number': 'asc'};

  const refresh = (resp, isBack) => {
    o_.exec.hide('de-loading');
    console.log(resp);
    o_.exec.show('data-search-results-container');
    const tokens = Formant.getTokens();
    ResultView.setResultState({
      results: resp,
      tokens: tokens,
    });
    ResultView.render();
    if (!isBack) {
      const searchParams = new URLSearchParams();
      for (const key in tokens) {
        searchParams.append(key, tokens[key].value);
      }
      const qs = searchParams.toString();
      if (qs) {
        let url = `${document.location.origin}${document.location.pathname}?${qs}`;
        window.history.pushState({}, '', url)
      }
    }
  }

  const removeFilter = (key) => {
    o_.exec.show('de-loading');
    Formant.removeFilter(key)
      .then((resp) => {
        refresh(resp);
      });
  };

  const addFilter = (data) => {
    Formant.addFilters(data)
      .then((resp) => {
        refresh(resp);
      })
  }

  const toPage = (page) => {
    Formant.setSearchParams({range: ResultView.getPagination()['range']});
    Formant.search()
      .then(resp => {
        refresh(resp);
      });
  };

  ResultView.init({
    removeFilter: removeFilter,
    addFilter: addFilter,
    toPage: toPage
  });

  const init = (isBack) => {
    if (document.location.search) {
      o_.exec.show('de-loading');
      const urlParams = new URLSearchParams(document.location.search);
      const params = Object.fromEntries(urlParams);
      console.log('searchParams', params);
      Formant.setSearchParams({sort: [searchSort]});
      Formant.setFilters(params)
        .then( (resp) => {
          refresh(resp, isBack);
        });
    }
  };

  
  /******* Formant: Form Module *******/
  const formantOptions = {
    helpers: {
      fetch: o_.fetch,
    },
    selectCallbacks: {
      collector_input__exclude: (entity, options, args) => {
        const autocompleteInput = document.getElementById('form-collector');
        const dropdownList = document.getElementById('form-collector__dropdown');
        const targetInput = document.getElementById('form-collector_id');

        dropdownList.innerHTML = '';
        console.log(options);
        options.forEach( v => {
          let choice = document.createElement('li');
          choice.classList.add('uk-flex', 'uk-flex-between');
          let display = `${v.full_name_en} ${v.full_name}`;
          choice.dataset.display = display;
          choice.dataset.pid = v.id;
          choice.innerHTML = `
            <div class="uk-padding-small uk-padding-remove-vertical">${display}</div>
            <div class="uk-padding-small uk-padding-remove-vertical uk-text-muted">${v.abbreviated_name}</div>`;
          choice.onclick = (e) => {
            dropdownList.setAttribute('hidden', '');
            autocompleteInput.value = e.currentTarget.dataset['display'];
            targetInput.value = e.currentTarget.dataset['pid'];
          }
          dropdownList.appendChild(choice);
        });
      }
    },
    intensiveRelation: {
      taxon_id: {
        model: 'closureTable',
        childrenQuery: 'options=1',
        higherCategory: 'higher_classification',
        categoryName: 'rank',
        optionPath: 'ranks',
      },
      named_area_id: {
        model: 'adjacencyList',
        childrenQuery: 'options=1',
        higherCategory: 'higher_area_classes',
        categoryName: 'area_class_id',
        optionPath: 'options'
      }
    }
  };
  Formant.register('adv-search-form', formantOptions);
  Formant.init()
    .then( () => {
      init();
    });

  const renderSearchbarDropdownItems = (data) => {
    // clear
    searchbarDropdownList.innerHTML = '';

    const handleItemClick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      const selectedIndex = e.currentTarget.dataset['key'];
      const selectedData = data[selectedIndex];
      const term = selectedData.meta.term;
      //console.log(term, selectedData);
      o_.exec.show('de-loading');
      if (term === 'field_number_with_collector') {
        addFilter({
          collector_id: selectedData.collector.id,
          collector_input__exclude: selectedData.collector.display_name,
          field_number: selectedData.field_number,
        });
      } else if (term === 'field_number') {
        addFilter('field_number', selectedData.field_number);
      } else if (term === 'collector') {
        addFilter({
          collector_id: selectedData.id,
          collector_input__exclude: selectedData.display_name,
        });
      } else if (term === 'taxon') {
        addFilter({
          taxon_id: selectedData.id
        });
      } else if (term === 'named_area') {
        addFilter({
          'named_area_id': selectedData.id
        });
      } else {
        addFilter({
          [term]: data[selectedIndex].value
        });
      }

      searchbarInput.value = '';
      o_.exec.hide('data-search-searchbar-dropdown');
    };

    data.forEach((item, index) => {
      const { label, display } = item.meta;
      let choice = o_.make(
        'li',
        {onclick: handleItemClick, 'data-key': index, 'class': 'uk-flex uk-flex-between'},
        o_.make('div', {'class': 'uk-padding-small uk-padding-remove-vertical'}, display),
        o_.make('div', {'class': 'uk-padding-small uk-padding-remove-vertical uk-text-muted'}, label)
      );
      searchbarDropdownList.appendChild(choice);
    });
  };

  searchbarInput.addEventListener('input', (e) => {
    const q = e.target.value;
    if (q.length > 0) {
      const endpoint = `/api/v1/searchbar?q=${q}`;
      o_.fetch(endpoint)
        .then( resp => {
          if (resp.data.length > 0) {
            searchbarInput.classList.remove('uk-form-danger')
            renderSearchbarDropdownItems(resp.data);
          } else {
            searchbarInput.classList.add('uk-form-danger')
          }
        })
        .catch( error => {
          console.log(error);
        });
    } 
  });
  searchbarInput.addEventListener('focus', (e) => {
    o_.exec.show('data-search-searchbar-dropdown');
  });

  searchbarInput.addEventListener('blur', (e) => {
    // delay hide dropdown wait if click on item
    setTimeout(() => {
      o_.exec.hide('data-search-searchbar-dropdown');
    }, 200)
  });

  // Sort nav
  for (let nav of sortItems) {
    nav.onclick = (e) => {
      e.preventDefault()
      sortLabel.innerHTML = `Sort: ${e.target.innerHTML}`
      UIkit.dropdown('#sort-select').hide(false)
      if (e.target.dataset.desc === '1') {
        searchSort = [{[e.target.dataset.sort]: 'desc'}];
      } else {
        searchSort = [{[e.target.dataset.sort]: 'asc'}];
      }
      Formant.setSearchParams({sort: searchSort});
      Formant.search()
        .then(resp => {
          refresh(resp);
        });
    }
  }

  window.addEventListener("popstate", (event) => {
    console.log(`location: ${document.location}, state: ${JSON.stringify(event.state)}`,);
    init(true);
  });

})();
