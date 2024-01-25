import {default as o_} from './common-snail.js';
o_.o =  {
  show: (id) => { document.getElementById(id).removeAttribute('hidden'); },
  hide: (id) => { document.getElementById(id).setAttribute('hidden', ''); },
};

const ResultView = (() => {
  //const ACCEPTED_VIEWS = ['table', 'list', 'map', 'gallery', 'checklist'];
  const resultText = o_.find('#data-search-results-text');
  const tokenList = o_.find('#search-data-tokens');

  let pagination = {
    page:1,
    count: 1,
    size: 20,
  };

  let state = {
    view: 'table',
    results: [],
    tokens: {},
  }

  let callbackFunctions = null;


  const getPagination = () => {
    return {
      ...pagination,
      range: [
        (pagination.page-1) * pagination.size,
        pagination.page*pagination.size
      ]
    };
  }

  const _setPaginationCount = (total) => {
    pagination.count = Math.ceil(total / pagination.size) || 1;
    return pagination.count;
  }

  const _renderPagination = () => {
    const container = document.getElementById('data-search-pagination');
    container.innerHTML = '';
    for(let i=1; i<=pagination.count; i++) {
      let item = document.createElement('li');
      if (i === pagination.page) {
        item.classList.add('uk-active');
      }
      let link = document.createElement('a');
      link.setAttribute('href', '#');
      link.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        pagination.page = parseInt(e.target.innerHTML, 10);
        callbackFunctions.toPage(pagination.page);
      };
      link.textContent = i;
      item.appendChild(link);
      container.appendChild(item);
    }
  }

  const _renderTokens = (tokens) => {
    tokenList.innerHTML = '';
    for (const key in tokens) {
      let item = tokens[key];
      let token = o_.make(
        'div',
        o_.make(
          'div', {'class': 'uk-card data-search-token uk-border-rounded'},
          o_.make(
            'div', {'class': 'uk-flex uk-flex-middle'},
            o_.make(
              'div',
              o_.make(
                'span', {'class': 'uk-label uk-label-success'},
                item.label,
              ),
              ` = ${item.displayValue}`
            ),
            o_.make(
              'button',
              {'class': 'uk-margin-left', 'type': 'button', 'uk-close': '', onclick: (e) => callbackFunctions.removeFilter(key) }
            )
          )
        )
      );
      tokenList.appendChild(token);
    }
  }

  const _renderDetailLink = (id, text) => {
    return o_.make('a', {'class': 'uk-link-reset', href: `/specimens/HAST:${id}`}, text);
  };

  const _renderFilterLink = (label, key, value) => {
    return o_.make(
      'div',
      {'class': 'add-filter-wrapper', 'uk-tooltip': 'title: click to add filter; pos: top;'},
      o_.make('span', label, {'class': 'add-filter', onclick: (e) => {
        callbackFunctions.addFilter({[key]: value});
      }})
    );
  }

  const _renderResultTable = (items) => {
    let contents = o_.find('#data-search-results-tbody');
    contents.innerHTML = '';

    const range = getPagination()['range'];

    for (let [index, item] of items.entries()) {
      let img = null;
      let taxon_text = '';
      if (item.image_url) {
        img = o_.make('img', {"class": "uk-preserve-width uk-border-rounded", src: item.image_url, width: '40', height: '40', alt: ''});
      }
      const namedAreas = [];
      for (const i in item.named_areas) {
        if (item.named_areas[i].area_class_id < 5) {
          namedAreas.push(o_.make('div', _renderFilterLink(item.named_areas[i].name, 'named_area_id', item.named_areas[i].id)));
        } else {
          namedAreas.push(o_.make('div', item.named_areas[i].name));
        }
      }
      const row = o_.make(
        'tr',
        o_.make('td', `${index+1+range[0]}`),
        o_.make('td', o_.make('a', {'class': 'uk-link-reset', href: `/specimens/HAST:${item.accession_number}`}, img)),
        o_.make('td', _renderDetailLink(item.accession_number, item.accession_number)),
        o_.make('td', `${item.type_status.charAt(0).toUpperCase() + item.type_status.slice(1)}`),
        o_.make('td', (item.taxon_text) ? _renderFilterLink(item.taxon_text, 'taxon_id', item.taxon.id ): ''),
        o_.make('td', o_.make('span', (item.collector) ? _renderFilterLink(item.collector.display_name, 'collector_id', item.collector.id) : ''), (item.field_number) ? o_.make('span', {'class': 'uk-text-bold'}, ` ${item.field_number}`) : ''),
        o_.make('td', (item.collect_date) ? _renderFilterLink(item.collect_date, 'collect_date', item.collect_date) : ''),
        o_.make('td', ...namedAreas)
      );
      contents.appendChild(row);
    }
  };

  const _renderResultList = (results) => {
    const resultContainer = o_.find('#data-search-result-list');
    resultContainer.innerHTML = '';
    results.forEach( x => {
      const collector = (x.collector) ? x.collector.display_name : '';
      const namedAreas = x.named_areas.map(na => na.display_name).join(', ');
      const img =  o_.make(
        'img', {
          src: x.image_url.replace('_s', '_m'),
          'width': '150',
          'alt': 'Specimen Image'
        });
      const infoWrapper = o_.make('div', {'class': 'uk-width-expand'});
      const info_text = `<p class="uk-text-large uk-margin-remove-bottom">${x.taxon_text}</p>
           <p class="uk-text-muted uk-margin-remove-top">
            <b>館號:</b> ${x.accession_number}<br />
            <b>採集者/採集號:</b> ${collector} ${x.field_number}<br />
            <b>採集日期:</b> ${x.collect_date}<br />
            <b>採集地:</b> ${namedAreas}</p>`;
      infoWrapper.innerHTML = info_text;
      const link_info = _renderDetailLink(x.accession_number, infoWrapper);
      let item = o_.make(
        'div',
        {'uk-grid': ''},
        o_.make(
          'div', {'class': 'uk-width-1-5'},
          _renderDetailLink(x.accession_number, img)
        ),
        o_.make(
          'div', {'class': 'uk-width-expand'},
          link_info,
        ),
      );
      resultContainer.appendChild(item);
    });
  };

  const init = (callbacks) => {
    callbackFunctions = callbacks;

    // nav view tabs
    const viewTabs = document.querySelector('#search-result-view-tab').childNodes;

    for (const node of viewTabs) {
      if (node.nodeName === 'LI') {
        //console.log(node, node.nodeType, node.nodeName);
        node.onclick = (e) => {
          e.preventDefault();
          e.stopPropagation();
          const item = e.currentTarget;
          state.view = item.dataset.view;
          UIkit.tab('#search-result-view-tab').show(item.dataset.tab);
          switch(state.view)
          {
            case 'table':
            case 'list':
            case 'gallery':
            if (state.results && state.results.data) {
              render();
            } else {
              //exploreData();
            }
            break;
            case 'map':
            /*
            if (state.resultsMap && state.resultsMap.data) {
              refreshResult();
            } else {
              exploreData();
              }
            */
            break;
            case 'checklist':
            /*
            if (state.resultsChecklist && state.resultsChecklist.data) {
              refreshResult();
            } else {
              exploreData();
              }
            */
            break;
          }
        };

        if (state.view === node.dataset.view) {
          UIkit.tab('#search-result-view-tab').show(node.dataset.tab);
        }
      }
    }
  }; // end of init

  const setResultState = (newState) => {
    state = {
      ...state,
      ...newState,
    }
    return state;
  }

  const render = () => {
    const results = state.results;
    const tokens = state.tokens;
    const resultsViewList = o_.find('.data-search-result-view');
    // show selected view result
    for (let i = 0; i < resultsViewList.length; i++) {
      //console.log(resultsViewList[i].id);
      resultsViewList[i].setAttribute('hidden', '');
      if (resultsViewList[i].dataset.view === state.view) {
        const resultWrapper = o_.find(`#data-search-result-${state.view}`);
        resultWrapper.removeAttribute('hidden');
      }
    }

    if (['table', 'list', 'gallery'].includes(state.view)) {
      resultText.innerHTML = `筆數: ${results.total.toLocaleString()} <span class="uk-text-muted uk-text-small">(${results.elapsed.toFixed(2)} 秒)</span>`;

      switch (state.view) {
      case 'table':
        _renderResultTable(results.data);
        break;
      case 'list':
        _renderResultList(results.data);
        break;
      }
      _renderTokens(tokens);
      _setPaginationCount(results.total);
      _renderPagination();
    }

  };

  return { init, render, getPagination, setResultState };
})();


export { ResultView };
