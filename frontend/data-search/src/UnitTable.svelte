<script>
  import { HOST, pagination } from './stores.js';
  export let rows= [];

  const handleClick = (accession_number) => {
    location.href = `${$HOST}/specimens/HAST:${accession_number}`;
  }
</script>


<table class="uk-table uk-table-small uk-table-striped uk-table-middle uk-table-hover uk-table-divider data-search-result-view" data-view="table" id="data-search-result-table">
  <thead>
    <tr>
      <th class="uk-table-shrink">#</th>
      <th class="uk-table-shrink">標本照</th>
      <th class="uk-table-shrink">館號</th>
      <th class="uk-table-shrink">模式標本</th>
      <th class="uk-width-medium">物種</th>
      <th class="uk-width-small">採集號</th>
      <th class="uk-width-small">採集日期</th>
      <th class="uk-table-shrink uk-text-nowrap">採集地點</th>
    </tr>
  </thead>
  <tbody id="data-search-results-tbody">
    {#each rows as row, index}
      <tr on:click={() => handleClick(row.accession_number)}>
        <td>{($pagination.page*$pagination.perPage) + index + 1}</td>
        <td><img src="{row.image_url}"></td>
        <td>{row.accession_number}</td>
        <td>{row.type_status}</td>
        <td>{row.taxon_text}</td>
        <td>{row.collector.display_name} {row.field_number}</td>
        <td>{row.collect_date}</td>
        <td>---</td>
      </tr>
    {/each}
  </tbody>
</table>
