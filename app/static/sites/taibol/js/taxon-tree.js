(function () {
  'use strict';

  const taxonTree = document.getElementById('taxonTree');
  const loading = document.getElementById('loading');

  const hide = (elem) => { elem.style.display = 'none'; };
  const show = (elem) => { elem.style.display = 'block'; };

  const fetchData = async (url) => {
    try {
      let response = await fetch(url);
      return await response.json();
    } catch(error) {
      console.error(`fetch error) ${error} | ${url}`);
      return error.message;
    }
  };

  const fetchURLs = async (urls) => {
    return await Promise.all(urls.map( async ([key, url]) => {
      let res = await fetchData(url);
      return [key, res.data];
    }));
  };

  let params = new URL(document.location).searchParams;

  const COL_MAP = {
    material_sample: 6,
    barcode: 7,
  };

  const TAXON_RANKS = [
    'kingdom_name',
    'phylum_name',
    'class_name',
    'order_name',
    'family_name',
    'genus_name',
    'species_name'
  ];

  const KINGDOM_ZH = {
    Animalia: '動物',
    Fungi: '真菌',
  };
  const TAXON_RANKS_ZH = {
    'kangdom_name': '界',
    'phylum_name': '門',
    'class_name': '綱',
    'order_name': '目',
    'family_name': '科',
    'genus_name': '屬',
    'species_name': '種',
  };

  const getRankLabels = async (rank, name) => {
    let ranks = [];
    let rankIndex = TAXON_RANKS.indexOf(rank);
    ranks = TAXON_RANKS.slice(rankIndex+1, 5).concat(['species_name'])
    let urls = (ranks).map((field) => {
      let filtr = {
        sourceData: {
          filters: {
            [rank]: name,
          },
          annotate: {
            values: [field],
            aggregate: 'count',
          },
          count: true,
        },
        collection_id: [COL_MAP[params.get('collection')]],
      };
      return [field, `/api/v1/search?filter=${JSON.stringify(filtr)}`];
    });
    let filtr = {
      sourceData: {
        filters: {
          [rank]: name,
        },
        count: true,
      },
      collection_id: [COL_MAP[params.get('collection')]],
    };
    urls.push(['record', `/api/v1/search?filter=${JSON.stringify(filtr)}`]);
    //console.log(urls);
    return fetchURLs(urls)
      .then(data => {
        let labels = data.map( x => {
          if (x[0] !== 'record') {
            return `${x[1]}${TAXON_RANKS_ZH[x[0]]}`;
          } else {
            return ` | ${x[1]} 筆`;
          }
        });
        return labels.join('');
      });
  };

  const fetchChildren = async (rootElem, rank, value) => {
    show(loading);
    let aggregateIndex = (TAXON_RANKS.indexOf(rank) >= 0 && TAXON_RANKS.indexOf(rank) < TAXON_RANKS.length) ? TAXON_RANKS.indexOf(rank) + 1 : '';
    let childField = TAXON_RANKS[aggregateIndex];
    let filtr = {
      sourceData: {
        filters: {
          [rank]: value
        },
        annotate: {
          values: ['kingdom_name', childField],
          //aggregate: 'count',
        }
      },
      collection_id: [COL_MAP[params.get('collection')]],
    };

    let ul = document.createElement('ul');
    ul.classList.add('taxonTree__items');
    let results = await fetchData(`/api/v1/search?filter=${JSON.stringify(filtr)}`);
    console.log(results);
    let childrens = await Promise.all(results.data.map( async (item) => {
      const li = document.createElement('li');
      const title = document.createElement('div');
      title.classList.add('taxonTree__title', 'closed');
      title.dataset.rankKey = `${childField}:${item[1]}`;
      //title.innerHTML = item[1];

      if (childField === 'species_name') {
        const taxonLink = document.createElement('a');
        taxonLink.textContent = item[1];
        taxonLink.href = `/data?kingdom=${item[0]}&collection=${params.get('collection')}&q=${item[1]}`;
        taxonLink.target = '_blank';
        title.classList.remove('closed');
        title.appendChild(taxonLink);
      } else {
        const taxonToggle = document.createElement('span');
        let rankLabel = await getRankLabels(childField, item[1]);

        let filter_zh = {
          sourceData: {
            filters: {
              [`${childField}`]: item[1],
              [`${childField}_zh`]: '__NOT_NULL__',
            },
                response: 'source_data',
          },
          collection_id: [COL_MAP[params.get('collection')]],
        };
        let zhRes = await fetchData(`/api/v1/search?filter=${JSON.stringify(filter_zh)}&range=${JSON.stringify([0, 1])}`);
        let zhLabel = '';
        if (zhRes.data.length > 0 && zhRes.data[0].source_data[`${childField}_zh`]) {
          zhLabel = zhRes.data[0].source_data[`${childField}_zh`];
        }

        taxonToggle.textContent = `${zhLabel} ${item[1]} | ${rankLabel}`;
        taxonToggle.onclick = (e) => {
          e.preventDefault();
          const children = title.nextElementSibling;
          //console.log(children, title.dataset);
          if (children === null) {
            fetchChildren(title, childField, item[1]);
          } else {
            if (children.style.display === 'none') {
              children.style.display = 'block';
              title.classList.remove('closed');
              title.classList.add('opened');
            } else {
              children.style.display = 'none';
              title.classList.remove('opened');
              title.classList.add('closed');
            }
          }
        };
        title.appendChild(taxonToggle);
      }
      li.appendChild(title);
      return li;
    }));
    hide(loading);
    childrens.forEach( x => {
      ul.appendChild(x);
    });
    rootElem.insertAdjacentElement('afterend', ul);
    /*
    fetch(`/api/v1/search?filter=${JSON.stringify(filtr)}`)
      .then( resp => resp.json())
      .then( result => {
        console.log(result);
        //let children = await Promise.all(result.data.map( async (item) => {
        //   console.log(item);
        // }));
        result.data.forEach(async (item) => {
          const li = document.createElement('li');
          const title = document.createElement('div');
          title.classList.add('taxonTree__title', 'closed');
          title.dataset.rankKey = `${childField}:${item[1]}`;
          //console.log(`${childField}:${item[1]}`);
          if (childField === 'species_name') {
            const taxonLink = document.createElement('a');
            taxonLink.textContent = item[1];
            taxonLink.href = `/data?kingdom=${item[0]}&collection=${params.get('collection')}&q=${item[1]}`;
            taxonLink.target = '_blank';
            title.classList.remove('closed');
            title.appendChild(taxonLink);
          } else {
            const taxonToggle = document.createElement('span');
            show(loading);
            let rankLabel = await getRankLabels(childField, item[1]);

            let filter_zh = {
              sourceData: {
                filters: {
                  [`${childField}`]: item[1],
                  [`${childField}_zh`]: '__NOT_NULL__',
                },
                response: 'source_data',
              },
              collection_id: [COL_MAP[params.get('collection')]],
            };
            let zhRes = await fetchData(`/api/v1/search?filter=${JSON.stringify(filter_zh)}&range=${JSON.stringify([0, 1])}`);
            let zhLabel = '';
            if (zhRes.data.length > 0 && zhRes.data[0].source_data[`${childField}_zh`]) {
              zhLabel = zhRes.data[0].source_data[`${childField}_zh`];
          }
            hide(loading);
            taxonToggle.textContent = `${zhLabel} ${item[1]} | ${rankLabel}`;
            taxonToggle.onclick = (e) => {
              e.preventDefault();
              const children = title.nextElementSibling;
              //console.log(children, title.dataset);
              if (children === null) {
                fetchChildren(title, childField, item[1]);
              } else {
                if (children.style.display === 'none') {
                  children.style.display = 'block';
                  title.classList.remove('closed');
                  title.classList.add('opened');
                } else {
                  children.style.display = 'none';
                  title.classList.remove('opened');
                  title.classList.add('closed');
                }
              }
            };
            title.appendChild(taxonToggle);
          }
          li.appendChild(title);
          ul.appendChild(li);
        });
        rootElem.insertAdjacentElement('afterend', ul);
        });
        */
  };
  const initKingdoms = async (rootElem) => {
    let ul = document.createElement('ul');
    ul.classList.add('taxonTree__root');
    let kingdoms = await Promise.all(['Animalia', 'Fungi'].map( async (kingdom) => {
      const li = document.createElement('li');
      const title = document.createElement('div');
      title.classList.add('taxonTree__title', 'closed');
      title.dataset.rankKey = `k:${kingdom}`;

      const taxonToggle = document.createElement('span');
      let rankLabel = await getRankLabels('kingdom_name', kingdom);
      taxonToggle.textContent = `${KINGDOM_ZH[kingdom]}界 ${kingdom} | ${rankLabel}`;
      title.appendChild(taxonToggle);
      taxonToggle.onclick = (e) => {
        e.preventDefault();
        const children = title.nextElementSibling;
        if (children === null) {
          fetchChildren(title, 'kingdom_name', kingdom);
        } else {
          if (children.style.display === 'none') {
            children.style.display = 'block';
            title.classList.remove('closed');
            title.classList.add('opened');
          } else {
            children.style.display = 'none';
            title.classList.remove('opened');
            title.classList.add('closed');
          }
        }
      };
      li.appendChild(title);
      //ul.appendChild(li);
      return li;
    }));
    kingdoms.forEach( x => {
      ul.appendChild(x);
    })
    rootElem.insertAdjacentElement('afterend', ul);

    hide(loading);
  }
  initKingdoms(taxonTree);

})();
