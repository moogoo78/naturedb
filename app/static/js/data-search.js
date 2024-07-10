(function() {
  'use strict';
  //let inputElem = document.getElementById('form-input');
  //let submitButton = document.getElementById('submit-button');
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


  // HTML template
  if ("content" in document.createElement("template")) {
  } else {
    alert('browser not support HTML template');
  }

  /*
  submitButton.onclick = (e) => {
    //console.log(inputElem.value);
    goSearch();
    };
  */

  const goSearch = () => {
    let params = new URL(document.location).searchParams;
    let filtr = {
    };
    let range = [
      (pagination.page-1) * pagination.numPerPage,
      pagination.page * pagination.numPerPage
    ];

    resultBody.innerHTML = '';
    fetch(`/api/v1/search?filter=${JSON.stringify(filtr)}&range=${JSON.stringify(range)}&sort=${JSON.stringify(["-created"])}`)
      .then( resp => resp.json())
      .then( result => {
        console.log(result);

        // render result
        resultTotal.textContent = result.total;
        result.data.forEach( item => {
          const clone = resultTemplate.content.cloneNode(true);
          let td = clone.querySelectorAll("td");
          //let x = item.source_data;
          let link = document.createElement('a');
          let img = document.createElement('img');
          img.src = `https://naturedb.s3.ap-northeast-1.amazonaws.com/ppi/${item.accession_number}-m.jpg`; // TODO
          img.width = '100';
          link.href = `/specimens/${item.unit_id}`;
          link.textContent = 'link';
          td[0].appendChild(link);
          td[1].appendChild(img);
          td[2].textContent = item.accession_number;
          td[3].textContent = item.taxon_text;
          td[4].textContent = (item.collector) ? item.collector.display_name : '';
          td[5].innerHTML = item.field_number;
          td[6].innerHTML = item.collect_date;
          td[7].innerHTML = item.locality_text;

          resultBody.appendChild(clone);
        });

        // render pagination
        resultPagination.innerHTML = '';
        let numPages = Math.ceil(result.total/pagination.numPerPage);
        let showList = [];
        // showList.push({
        //   label: '[',
        //   disabled: (pagination.page === 1) ? true : false,
        //   page: pagination.page-1,
        // });
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
        // showList.push({
        //   label: ']',
        //   disabled: (pagination.page === numPages) ? true : false,
        //   page: pagination.page+1,
        // });

        //console.log(showList);
        let containerLeft = document.createElement('span');
        containerLeft.textContent = '[ ';
        let containerRight = document.createElement('span');
        containerRight.textContent = ' ]';
        resultPagination.appendChild(containerLeft);
        for (let i=0; i<showList.length; i++) {
          let hasLink = true;
          let pageItem = document.createElement('span');
          if ('isActive' in showList[i] && showList[i].isActive === true) {
            hasLink = false;
          }
          if ('disabled' in showList[i] && showList[i].disabled === true) {
            hasLink = false;
          }
          if ('page' in showList[i]) {
            let pre = (i === 0) ? '' : '| ';
            if (hasLink === true) {
              pageItem.innerHTML = `${pre} <a class="page-link" href="#">${showList[i].page}</a> `;
              pageItem.onclick = (e) => {
                e.preventDefault();
                pagination.page = showList[i].page;
                goSearch();
              };
            } else {
              pageItem.innerHTML = ` ${pre} ${showList[i].page} `;
            }
          } else {
            // label
            pageItem.innerHTML = ` | ${showList[i].label} `;
          }
          resultPagination.appendChild(pageItem);
        }
        resultPagination.appendChild(containerRight);
      });
  };
  const init = () => {
    goSearch();
  };

  init();
})();
