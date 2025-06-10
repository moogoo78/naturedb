(function () {
  'use strict';

  const taxonTree = document.getElementById('taxonTree');
  const loading = document.getElementById('loading');
  const spinner = document.getElementById('spinner');

  const hideLoading = () => {
    loading.style.display = 'none';
    spinner.style.display = 'none';
  };
  const showLoading = () => {
    loading.style.display = 'block';
    spinner.style.display = 'block';
  };

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
    'kingdom',
    'phylum',
    'class',
    'order',
    'family',
    'genus',
    'species'
  ];
  const KINGDOM_ZH = {
    Animalia: '動物',
    Fungi: '真菌',
  };
  const TAXON_RANKS_ZH = {
    'kangdom': '界',
    'phylum': '門',
    'class': '綱',
    'order': '目',
    'family': '科',
    'genus': '屬',
    'species': '種',
  };

  const getRankStats = async (rawData) => {
    let filtr = {
      raw: rawData,
      collection_id: [COL_MAP[params.get('collection')]],
    };
    let res = await fetchData(`/api/v1/taxonomy/stats?filter=${JSON.stringify(filtr)}`);
    let ranks = TAXON_RANKS.slice(TAXON_RANKS.indexOf(res.rank) + 1, TAXON_RANKS.length);
    //console.log(res, filtr);
    let labels = ranks.map( x => {
      return `${res.data[x]}${TAXON_RANKS_ZH[x]}`;
    });
    let unit = (params.get('collection')=='barcode') ? '筆' : '件';
    labels.push(` | ${res.total}${unit}`);
    return labels.join('');
  };

  const fetchChildren = async (rootElem, rawData, kingdom) => {
    showLoading();
    //let aggregateIndex = (TAXON_RANKS.indexOf(rank) >= 0 && TAXON_RANKS.indexOf(rank) < TAXON_RANKS.length) ? TAXON_RANKS.indexOf(rank) + 1 : '';
    //let childField = TAXON_RANKS[aggregateIndex];

    let filtr = {
      raw: rawData,
      collection_id: [COL_MAP[params.get('collection')]],
    };

    let ul = document.createElement('ul');
    ul.classList.add('taxonTree__items');
    let results = await fetchData(`/api/v1/taxonomy/children?filter=${JSON.stringify(filtr)}`);
    console.log(results);
    let childRank = results.rank;
    let childrens = await Promise.all(results.data.map( async (child) => {
      const li = document.createElement('li');
      const title = document.createElement('div');
      title.classList.add('taxonTree__title', 'closed');

      if (childRank === 'species') {
        const taxonLink = document.createElement('a');
        taxonLink.textContent = child[1];
        taxonLink.href = `/data?kingdom=${kingdom}&collection=${params.get('collection')}&q=${child[1]}`;
        taxonLink.target = '_blank';
        title.classList.remove('closed');
        title.appendChild(taxonLink);
      } else {
        const taxonToggle = document.createElement('span');
        let rankStats = await getRankStats({ [childRank]: [`${childRank}_name`, child[0]] });
        taxonToggle.textContent = `${child[1]} ${child[0]} | ${rankStats}`;
        taxonToggle.onclick = (e) => {
          e.preventDefault();
          const children = title.nextElementSibling;
          if (children === null) {
            fetchChildren(title, {[childRank]: [`${childRank}_name`, child[0]]}, kingdom);
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

    hideLoading();
    childrens.forEach( x => {
      ul.appendChild(x);
    });
    rootElem.insertAdjacentElement('afterend', ul);
  };

  const initKingdoms = async (rootElem) => {
    let ul = document.createElement('ul');
    ul.classList.add('taxonTree__root');
    let kingdoms = await Promise.all(['Animalia', 'Fungi'].map( async (kingdom) => {
      const li = document.createElement('li');
      const title = document.createElement('div');
      title.classList.add('taxonTree__title', 'closed');
      //title.dataset.rankKey = `k:${kingdom}`;

      const taxonToggle = document.createElement('span');
      let rankStats = await getRankStats({ kingdom: ['kingdom_name', kingdom] });
      taxonToggle.textContent = `${KINGDOM_ZH[kingdom]}界 ${kingdom} | ${rankStats}`;
      title.appendChild(taxonToggle);
      taxonToggle.onclick = (e) => {
        e.preventDefault();
        const children = title.nextElementSibling;
        if (children === null) {
          fetchChildren(title, {'kingdom': ['kingdom_name', kingdom]}, kingdom);
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
    });
    rootElem.insertAdjacentElement('afterend', ul);
  };
  initKingdoms(taxonTree);

  })();
