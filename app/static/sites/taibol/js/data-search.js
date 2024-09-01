(function() {
  'use strict';
  let inputElem = document.getElementById('form-input');
  let submitButton = document.getElementById('submit-button');
  let resultTotal = document.getElementById('result-total');
  let resultBody = document.getElementById('result-body');
  let resultTemplate = document.getElementById('result-template');
  let resultPagination = document.getElementById('result-pagination');
  let pagination = {
    page: 1,
    numPerPage: 20,
    numPages: 1,
    pattern: 'A',
  };

  const COL_MAP = {
    material_sample: 6,
    barcode: 7,
  };

  // HTML template
  if ("content" in document.createElement("template")) {
  } else {
    alert('browser not support HTML template');
  }

  submitButton.onclick = (e) => {
    //console.log(inputElem.value);
    goSearch();
  };
  
  const goSearch = () => {
    let params = new URL(document.location).searchParams;
    let filtr = {
      sourceData: {
        q: inputElem.value,
        qFields: [
          'phylum_name',
          'phylum_name_zh',
          'class_name',
          'class_name_zh',
          'order_name',
          'order_name_zh',
          'family_name',
          'family_name_zh',
          'genus_name',
          'genus_name_zh',
          'species_name',
          'species_name_zh',
          'voucher_id',
          'unit_id',
          'note',
          'document_id',
          'collector',
          'collector_zh',
        ],
        filters: {
          kingdom_name: params.get('kingdom'),
          //record_type: TYPE_MAP[params.get('category')],
        }
      },
      collection_id: [COL_MAP[params.get('collection')],],
    };
    let range = [
      (pagination.page-1) * pagination.numPerPage,
      pagination.page * pagination.numPerPage
    ];

    resultBody.innerHTML = '';
    fetch(`/api/v1/search?filter=${JSON.stringify(filtr)}&range=${JSON.stringify(range)}`)
      .then( resp => resp.json())
      .then( result => {
        console.log(result);

        // render result
        resultTotal.textContent = result.total;
        result.data.forEach( item => {
          const clone = resultTemplate.content.cloneNode(true);
          let td = clone.querySelectorAll("td");
          let x = item.source_data;
          let link = document.createElement('a');
          //console.log(x);
          link.href = `/records/${item.record_id}`;
          //link.textContent = x.species_name;
          //td[0].textContent = x.species_name;
          let italicFont = document.createElement('i');
          italicFont.textContent = x.species_name;
          link.appendChild(italicFont);
          td[0].appendChild(link);
          td[1].textContent = (params.get('collection') === 'material_sample') ? x.unit_id : x.voucher_id;
          td[2].innerHTML = `${x.kingdom_name_zh}${x.kingdom_name}`;
          td[3].innerHTML = `${x.phylum_name_zh}${x.phylum_name}`;
          td[4].innerHTML = `${x.class_name_zh}${x.class_name}`;
          td[5].innerHTML = `${x.order_name_zh}${x.order_name}`;
          td[6].innerHTML = `${x.family_name_zh}${x.family_name}`;
          let common_name = '';
          if ('species_name_zh' in x) {
            common_name = x['species_name_zh'];
          }
          td[7].textContent = (common_name.indexOf(['0', '']) < 0) ? common_name : '';
          //img
          let img = document.createElement('img');
          img.setAttribute('height', '50');
          if (params.get('collection') === 'material_sample') {
            img.src = `https://brmas-taibol.s3.ap-northeast-1.amazonaws.com/dpi200/${x.unit_id}.jpg`;
          } else {
            img.src = `https://brmas-taibol.s3.ap-northeast-1.amazonaws.com/dpi200/${x.voucher_id}.jpg`;
          }
          td[8].appendChild(img);
          resultBody.appendChild(clone);
        });

        // render pagination
        //console.log(pagination);
        resultPagination.innerHTML = '';
        let numPages = Math.ceil(result.total/pagination.numPerPage);
        let showList = [];
        showList.push({
          label: '&lt;',
          disabled: (pagination.page === 1) ? true : false,
          page: pagination.page-1,
        });
        if (numPages <= 10) {
          for (let i=1; i<=numPages;i++) {
            showList.push({
              isActive: (pagination.page === i) ? true : false,
              page: i,
            });
          }
        } else {
          showList.push({
            page: 1,
            isActive: (pagination.page === 1) ? true : false,
          });
          if (pagination.page < 4) {
            // first 4
            showList.push({
              page: 2,
              isActive: (pagination.page === 2) ? true : false,
            });
            showList.push({
              page: 3,
              isActive: (pagination.page === 3) ? true : false,
            });

            showList.push({
              page: 4,
              isActive: (pagination.page === 4) ? true : false,
            });
            showList.push({
              label: '&hellip;',
            });
          } else if (pagination.page > numPages-3) {
            // last 3
            showList.push({
              label: '&hellip;',
            });
            showList.push({
              page: numPages-3,
              isActive: (pagination.page === numPages-3) ? true : false,
            });
            showList.push({
              page: numPages-2,
              isActive: (pagination.page === numPages-2) ? true : false,
            });

            showList.push({
              page: numPages-1,
              isActive: (pagination.page === numPages-1) ? true : false,
            });
          } else {
            // middle
            showList.push({
              label: '&hellip;',
            });
            showList.push({
              page: pagination.page-1,
              isActive: false,
            });
            showList.push({
              label: pagination.page,
              isActive: true,
            });
            showList.push({
              page: pagination.page+1,
              isActive: false,
            });
            showList.push({
              label: '&hellip;',
            });
          }
          showList.push({
            page: numPages,
            isActive: (pagination.page === numPages) ? true : false,
          });
        }
        showList.push({
          label: '&gt;',
          disabled: (pagination.page === numPages) ? true : false,
          page: pagination.page+1,
        });
        for (let i=0; i<showList.length; i++) {
          let pageItem = document.createElement('li');
          pageItem.classList.add('page-item');
          if ('isActive' in showList[i] && showList[i].isActive === true) {
            pageItem.classList.add('active');
          }
          if ('disabled' in showList[i] && showList[i].disabled === true) {
            pageItem.classList.add('disabled');
          }
          if ('page' in showList[i]) {
            if ('label' in showList[i]) {
              pageItem.innerHTML = `<a class="page-link" href="#">${showList[i].label}</a>`;
            } else {
              pageItem.innerHTML = `<a class="page-link" href="#">${showList[i].page}</a>`;
            }
            pageItem.onclick = (e) => {
              e.preventDefault();
              pagination.page = showList[i].page;
              goSearch();
            };
          } else if ('label' in showList[i]) {
            pageItem.innerHTML = `<span class="page-link">${showList[i].label}</span>`;
          }
          resultPagination.appendChild(pageItem);
        }
      });
  };
  const init = () => {
    goSearch();
  };

  init();
})();
