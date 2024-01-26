(function() {
  'use strict';
   var map = L.map('hast-map').setView([25.043114, 121.615507], 14);
 L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
   attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
 }).addTo(map);

  const html = `中央研究院植物標本館<br/>115 臺北市南港區研究院路二段128號<br/>
            電話：(02) 2787-2223 劉小姐<br/>
  Email：hast@sinica.edu.tw</pre>`;
  L.marker([25.043114, 121.615507]).addTo(map)
  .bindPopup(html)
  .openPopup();
})();
