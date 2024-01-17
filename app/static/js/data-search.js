import Formant from './search/formant.js';
import { ResultView } from './search/helper-results.js';
import {default as o_} from './common-snail.js';

(function() {
  "use strict";

  // helpers
  //const $create = (tag) => { return document.createElement(tag); }
  o_.exec =  {
    show: (id) => { document.getElementById(id).removeAttribute('hidden'); },
    hide: (id) => { document.getElementById(id).setAttribute('hidden', ''); },
  };

  // global state
  const state = {
    results: {},
    resultsView: 'table',
    resultsChecklist: {},
    resultsMap: {},
    map: null,
    mapMarkers: [],
  };

  const refresh = (resp) => {
    o_.exec.hide('de-loading');
    console.log(resp);
    o_.exec.show('data-search-results-container');
    ResultView.render('table', resp, Formant.getTokens());
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

  const init = () => {
    ResultView.init({
      removeFilter: removeFilter,
      addFilter: addFilter,
      toPage: toPage
    });
    Formant.init()
      .then( () => {
        // ## parse query string
        if (document.location.search) {
          const urlParams = new URLSearchParams(document.location.search);
          let toFetch = [];
          const params = Object.fromEntries(urlParams);
          console.log('params', params);
          //goSearch(params);
          o_.exec.show('de-loading');
          Formant.setFilters(params)
            .then( (resp) => {
              refresh(resp);
            });
        }
      });
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

  init();
})();
