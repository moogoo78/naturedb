(function() {
  'use strict';
  const bodyElement = document.getElementsByClassName('A4')[0];
  //const items = document.getElementsByClassName('hast-label-item');
  // return nodeList, if  getElementsByClassName will return HTMLCollection, automatically change DOM, cause "move to" side effect bug
  const items = document.querySelectorAll('.hast-label-item');

  //console.log(items);
  const heightLimit = 1123;
  let sheetCount = 1;
  let heightCount = 12; // h1 page-title height
  const buffer = [];
  const columns = []
  let itemRanges = [];

  const createSheet = (page) => {
    console.log('create page', page);
    const newSheet = document.createElement('div')
    const newPageTitle = document.createElement('h1');
    const newPageItemWrapper = document.createElement('div');
    const newPageItemColumnLeft = document.createElement('div');
    const newPageItemColumnRight = document.createElement('div');
    newSheet.classList.add('sheet');
    newPageTitle.classList.add('page-title');
    newPageTitle.innerHTML = `page ${page}`;
    newPageItemWrapper.classList.add('page-item-wrapper');
    newPageItemColumnLeft.classList.add('page-item-column', `column-${page}-1`);
    newPageItemColumnRight.classList.add('page-item-column', `column-${page}-2`);
    newSheet.appendChild(newPageTitle);
    newSheet.appendChild(newPageItemWrapper);
    newPageItemWrapper.appendChild(newPageItemColumnLeft);
    newPageItemWrapper.appendChild(newPageItemColumnRight);
    bodyElement.appendChild(newSheet);
  }

  for (let i=0; i<items.length;i++) {
    itemRanges.push(i);
    heightCount += items[i].offsetHeight + 20; // margin: 10px
    const nextHeight = (i < items.length -1) ? items[i+1].offsetHeight + 20 : 0;
    console.log(`${i}), item H: ${items[i].offsetHeight}, next item H: ${nextHeight}, count H: ${heightCount}`);
    if (heightCount + nextHeight >= heightLimit) { // A4 height px in 96 PPI
      columns.push(itemRanges);
      heightCount = 0;
      itemRanges = [];

      console.log(items.length, columns.length, i);
      if (i >= 2 && columns.length % 2 === 0) {
        sheetCount++;
        //createSheet( (columns.length+1)/2+1);
        createSheet(sheetCount);
      }
    }
  }
  // last
  if (itemRanges.length > 0) {
    columns.push(itemRanges);
  }
  console.log('columns', columns);

  if (columns.length >= 2) {
    const firstContainer = document.getElementsByClassName('column-1-2')[0];
    const itemsToMove = columns[1].map((x)=>{
      firstContainer.appendChild(items[x])
      return items[x]
    });

    // start move after 2 columns
    for (let i=2; i < columns.length; i++) {
      //if (i % 2 === 0) {
      const page = parseInt(i/2) + 1;
      const columnIndex = (i%2 === 0) ? '1' : '2';
      const container = document.getElementsByClassName(`column-${page}-${columnIndex}`)[0];
      const itemsToMove = columns[i].map((x)=>{
        console.log(items[x], container, page, columnIndex);
        container.appendChild(items[x])
        return items[x]
      });
      //console.log(itemsToMove);
    }
  } else {
    console.log('no need to move');
  }
})();
