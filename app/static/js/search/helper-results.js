import {default as o_} from '../common-snail.js';
o_.o =  {
  show: (id) => { document.getElementById(id).removeAttribute('hidden'); },
  hide: (id) => { document.getElementById(id).setAttribute('hidden', ''); },
};

const ResultView = (() => {
  //const ACCEPTED_VIEWS = ['table', 'list', 'map', 'gallery', 'checklist'];
  let data = [];
  let pagination = {
    page:1,
    count: 1,
    size: 20,
  };
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
    const tokenList = o_.find('#search-data-tokens');
    tokenList.innerHTML = '';
    for (const key in tokens) {
      let item = tokens[key];
      let token = o_.make(
        'div',
        o_.make(
          'div', {'class': 'uk-card de-token uk-border-rounded'},
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
  const _appendUrl = (tokens) => {
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

  const _renderResultTable = (items) => {
    const renderDetailLink = (id, text) => {
      return o_.make('a', {'class': 'uk-link-reset', href: `/specimens/HAST:${id}`}, text);
    };

    const renderFilterLink = (label, key, value) => {
      return o_.make(
        'div',
        {'class': 'add-filter-wrapper', 'uk-tooltip': 'title: click to add filter; pos: top;'},
        o_.make('span', label, {'class': 'add-filter', onclick: (e) => {
          callbackFunctions.addFilter({[key]: value});
        }})
      );
    }
    let contents = o_.find('#data-search-results-tbody');
    contents.innerHTML = '';

    const range = getPagination()['range'];

    for (let [index, item] of items.entries()) {
      let img = null;
      let taxon_text = '';
      if (item.image_url) {
        img = o_.make('img', {"class": "uk-preserve-width uk-border-rounded", src: item.image_url, width: '40', height: '40', alt: ''});
      }
      if (item.taxon) {
        //taxon = renderFilterLink(item.accession_number, );
      }
      const namedAreas = [];
      for (const i in item.named_areas) {
        if (item.named_areas[i].area_class_id < 5) {
          namedAreas.push(o_.make('div', renderFilterLink(item.named_areas[i].name, 'named_area_id', item.named_areas[i].id)));
        } else {
          namedAreas.push(o_.make('div', item.named_areas[i].name));
        }
      }
      const row = o_.make(
        'tr',
        o_.make('td', `${index+1+range[0]}`),
        o_.make('td', o_.make('a', {'class': 'uk-link-reset', href: `/specimens/HAST:${item.accession_number}`}, img)),
        o_.make('td', renderDetailLink(item.accession_number, item.accession_number)),
        o_.make('td', `${item.type_status.charAt(0).toUpperCase() + item.type_status.slice(1)}`),
        o_.make('td', (item.taxon_text) ? renderFilterLink(item.taxon_text, 'taxon_id', item.taxon.id ): ''),
        o_.make('td', o_.make('span', (item.collector) ? renderFilterLink(item.collector.display_name, 'collector_id', item.collector.id) : ''), (item.field_number) ? o_.make('span', {'class': 'uk-text-bold'}, ` ${item.field_number}`) : ''),
        o_.make('td', (item.collect_date) ? renderFilterLink(item.collect_date, 'collect_date', item.collect_date) : ''),
        o_.make('td', ...namedAreas)
      );
      contents.appendChild(row);
    }
  };

  const init = (callbacks) => {
    callbackFunctions = callbacks
  }

  const render = (view, results, tokens) => {
    const resultText = o_.find('#data-search-results-text');

    if (['table', 'list', 'gallery'].includes(view)) {
      resultText.innerHTML = `筆數: ${results.total.toLocaleString()} <span class="uk-text-muted uk-text-small">(${results.elapsed.toFixed(2)} 秒)</span>`;

      switch (view) {
      case 'table':
        _renderResultTable(results.data);
        break;
      }
      _renderTokens(tokens);
      _appendUrl(tokens);
      _setPaginationCount(results.total);
      _renderPagination();
    }

  };

  return { init, render, getPagination };
})();


export { ResultView };
