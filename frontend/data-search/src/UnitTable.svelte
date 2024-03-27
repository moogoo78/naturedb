<script>
  import { HOST, pagination } from './stores.js';
  export let rows= [];

  let expands = rows.map( _ => false);
  const handleClick = (accession_number) => {
    location.href = `${$HOST}/specimens/HAST:${accession_number}`;
  }

  const handleExpand = (index) => {
    expands[index] = !expands[index];
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
      <th class="uk-width-small">年份</th>
      <th class="uk-table-shrink uk-text-nowrap">地點</th>
      <th class=""></th>
    </tr>
  </thead>
  <tbody id="data-search-results-tbody">
    {#each rows as row, index}
      <tr>
        <td>{($pagination.page*$pagination.perPage) + index + 1}</td>
        <td><img src="{row.image_url}"></td>
        <td><a class="uk-link" href="{$HOST}/specimens/HAST:{row.accession_number}" target="_blank">
{row.accession_number}</a></td>
        <!-- <td>{row.type_status}</td> -->
        <td>{row.taxon_text}</td>
        <td>{row.collector.display_name} <strong>{row.field_number}</strong> </td>
        <td>{row.collect_date.split('-')[0]}</td>
        <td>---</td>
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
