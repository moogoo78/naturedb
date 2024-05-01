<script>
  import { HOST } from './stores.js';
  import { formant } from './formant.js';

  export let rows= [];
  export let start = 0;

  let expands = rows.map( _ => false);
  const handleClick = (accession_number) => {
    location.href = `${$HOST}/specimens/HAST:${accession_number}`;
  }

  const handleExpand = (index) => {
    expands[index] = !expands[index];
  }

  const handleAdd = (props) => {
    formant.addFilter(props);
    formant.goSearch();
  }
</script>

<table class="uk-table uk-table-small uktable-middle uk-table-hover uk-table-divider data-search-result-view" data-view="table" id="data-search-result-table">
  <thead>
    <tr>
      <th class="uk-table-shrink">#</th>
      <th class="uk-table-shrink">標本照</th>
      <th class="uk-table-shrink">館號</th>
      <!-- <th class="uk-table-shrink">模式標本</th> -->
      <th class="uk-width-medium">物種</th>
      <th class="uk-width-small">採集號</th>
      <th class="uk-table-shrink">年份</th>
      <th class="uk-text-nowrap">地點</th>
      <th class="uk-table-shrink">展開</th>
    </tr>
  </thead>
  <tbody id="data-search-results-tbody">
    {#each rows as row, index}
      <tr>
        <td>{start + index}</td>
        <td><img src="{row.image_url}"></td>
        <td>{#if row.type_status}<span class="uk-label uk-label-success">{row.type_status.toUpperCase()}</span>{/if} <a class="uk-link" href="{$HOST}/specimens/HAST:{row.accession_number}" target="_blank">
{row.accession_number}</a></td>
        <!-- <td>{row.type_status}</td> -->
        <td><a href="#" uk-tooltip="title: 加入篩選" class="uk-link-text" on:click|preventDefault={() => { handleAdd({scientific_name: {display: row.taxon_text, value: row.taxon.id , name: 'scientific_name'}}); }}>{row.taxon_text}</a></td>
        <td><a href="#" uk-tooltip="title: 加入篩選" class="uk-link-text" on:click|preventDefault={() => { handleAdd({collector: {display: row.collector.display_name, value: row.collector.id , name: 'collector'}}); }}>{row.collector.display_name}</a> <strong>{row.field_number}</strong> </td>
        <td>{row.collect_date.split('-')[0]}</td>
        <td>{#each row.named_areas as na, index}{na.name}{#if index <= row.named_areas.length -1}/{/if}{/each}</td>
        <td><span uk-icon="{(expands[index] === true) ? 'minus-circle' : 'plus-circle'}" on:click={ () => handleExpand(index)}></span></td>
      </tr>
    <tr class="{(expands[index] === true)? '' : 'uk-hidden'}">
      <td colspan="8">
        <div class="" uk-grid>
          <div class="uk-width-1-3">
              <img src="{row.image_url.replace('_s', '_m')}" height="30" class="uk-height-medium"/>
          </div>
          <div class="uk-width-expand">
            <div class="uk-align-right"><a class="uk-button uk-button-primary" href="{$HOST}/specimens/HAST:{row.accession_number}" target="_blank"><span uk-icon="link"></span> Specimen / 標本</a></div>
            <table class="uk-table item-expand-wrapper">
              <!-- <caption>Table Caption</caption> -->
              <tbody>
                <tr>
                  <td>物種</td>
                  <td>{row.taxon_text}</td>
                </tr>
                <tr>
                  <td>採集者</td>
                  <td>{row.collector.full_name || ''}</td>
                </tr>
                <tr>
                  <td>採集者(英文)</td>
                  <td>{row.collector.full_name_en || ''}</td>
                </tr>
                <tr>
                  <td>採集日期</td>
                  <td>{row.collect_date || ''}</td>
                </tr>
                {#each row.named_areas as na}
                  <tr>
                    <td>{na.area_class.label}</td>
                    <td>{na.name}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      </td>
    </tr>
    {/each}
  </tbody>
</table>


<style>
  .item-expand-wrapper {
    border: 2px solid #faa05a;
    margin: 6px;
  }
</style>
