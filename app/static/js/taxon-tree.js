(function () {
  'use strict';

  const TAXON_RANKS = ['family', 'genus', 'species'];

  const fetchChildren = (rootElem, taxaFilter) => {
    const spinner = document.createElement('div');
    spinner.setAttribute('uk-spinner', '');
    rootElem.appendChild(spinner);
    fetch(`/api/v1/taxa?filter=${JSON.stringify(taxaFilter)}`)
      .then(resp => resp.json())
      .then(result => {
        spinner.remove();

        let ul = document.createElement('ul');
        if (taxaFilter.parent_id === null) {
          ul.classList.add('taxonTree__root');
        } else {
          ul.classList.add('taxonTree__items');
        }

        result.data.forEach((item) => {
          const li = document.createElement('li');
          const title = document.createElement('div');

          title.classList.add('taxonTree__title');
          title.classList.add('closed');
          title.dataset.taxonid = item.id;
          title.dataset.taxonrank = item.rank;
          let scname = item.full_scientific_name;
          if(item.common_name) {
            scname = `${scname} (${item.common_name})`;
          }
          if (item.rank === 'species') {
            const taxonLink = document.createElement('a');
            taxonLink.textContent = scname;
            taxonLink.href = `/species/${item.id}`;
            taxonLink.target = '_blank';
            title.classList.remove('closed');
            title.appendChild(taxonLink);
          } else {
            const taxonToggle = document.createElement('span');
            taxonToggle.textContent = scname;
            title.appendChild(taxonToggle);
            taxonToggle.onclick = (e) => {
              e.preventDefault();
              const children = title.nextElementSibling;
              //console.log(children, title.dataset);
              if (children === null) {
                const rankIndex = TAXON_RANKS.indexOf(taxaFilter.rank) + 1;
                fetchChildren(title, {parent_id: item.id, rank: TAXON_RANKS[rankIndex]});
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
            }
          }

          li.appendChild(title);
          ul.appendChild(li);
          rootElem.insertAdjacentElement('afterend', ul);
        });
      });
  };
  const taxonTree = document.getElementById('taxonTree');
  fetchChildren(taxonTree, {parent_id: null, rank: 'family'})
})();
