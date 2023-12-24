(function () {
  'use strict';

  const RANKS = ['family', 'genus', 'species'];

  const expandChildTaxa = ( parentElem ) => {
    let spinner = document.createElement('div');
    spinner.setAttribute('uk-spinner', '');
    parentElem.appendChild(spinner);

    const rankIndex = RANKS.indexOf(parentElem.dataset.taxonrank);
    const payload = {
      parent_id: parentElem.dataset.taxonid,
      rank: RANKS[rankIndex+1],
    };
    let ul = document.createElement('ul');
    fetch(`/api/v1/taxa?filter=${JSON.stringify(payload)}`)
      .then(resp => resp.json())
      .then(result => {
        //console.log(result);
        spinner.remove();
        ul.classList.add('taxon-tree-items');
        ul.classList.add('collapsed');
        result.data.forEach((item) => {
          let li = document.createElement('li');
          let subTitle = document.createElement('div');
          subTitle.dataset.taxonid = item.id;
          subTitle.dataset.taxonrank = item.rank;
          subTitle.classList.add('taxon-tree-title');
          subTitle.onclick = (e) => {
            e.preventDefault();
            expandChildTaxa(subTitle);
          }
          let scname = item.full_scientific_name;
          if(item.common_name) {
            scname = `${scname} (${item.common_name})`;
          }
          subTitle.textContent = scname;
          li.appendChild(subTitle);
          ul.appendChild(li);
          parentElem.insertAdjacentElement('afterend', ul);
        });
      });
  };
  /*
        function listree() {
            const subMenuHeadings = document.getElementsByClassName("listree-submenu-heading");
            Array.from(subMenuHeadings).forEach(function(subMenuHeading){
                subMenuHeading.classList.add("collapsed");
                subMenuHeading.nextElementSibling.style.display = "none";
                subMenuHeading.addEventListener('click', function(event){
                    event.preventDefault();
                    const subMenuList = event.target.nextElementSibling;
                    if(subMenuList.style.display=="none"){
                        subMenuHeading.classList.remove("collapsed");
                        subMenuHeading.classList.add("expanded");
                        subMenuList.style.display = "block";
                    }
                    else {
                        subMenuHeading.classList.remove("expanded");
                        subMenuHeading.classList.add("collapsed");
                        subMenuList.style.display = "none";
                    }
                    event.stopPropagation();
                });
            });
        }
  listree();*/
  console.log('init');
  const titleList = document.getElementsByClassName('taxon-tree-title');
  Array.from(titleList).forEach((title) => {
    title.onclick = (e) => {
      e.preventDefault();
      expandChildTaxa(title);
    }
  });
})();
