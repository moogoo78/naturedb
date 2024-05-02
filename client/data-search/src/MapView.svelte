<script>
  import { onMount } from 'svelte';

  export let rows = [];

  onMount(() => {
    let resultMap = L.map('data-search-result-map').setView([23.181, 121.932], 7);
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    }).addTo(resultMap);

    /*for(let i=0; i<state..length; i++) {
      state.map.removeLayer(state.mapMarkers[i]);
    }*/
    rows.forEach( (x) => {
      const html = `<div>館號: ${x.accession_number}</div><div>採集者:${x.collector.display_name}</div><div>採集號: ${x.field_number}</div><div>採集日期: ${x.collect_date}</div><div>物種: ${x.taxon_text}</div><div><a href="/specimens/HAST:${x.accession_number}" target="_blank">查看</a></div>`;
      const marker = L
            .marker([parseFloat(x.latitude_decimal), parseFloat(x.longitude_decimal)])
      //.addTo(state.map)
	.bindPopup(html)
        .openPopup();
      resultMap.addLayer(marker);
      //resultMap.mapMarkers.push(marker);
    });
  });


</script>
<div class="uk-text-muted uk-margin">有經緯度的資料筆數: {rows.length}</div>
<div id="data-search-result-map" data-view="map" class="data-search-result-view"></div>

<style>
  #data-search-result-map { height: 100vh }
</style>
