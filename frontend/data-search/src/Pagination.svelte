<script>
  import { pagination } from './stores.js';
  export let toPageCallback;

  $: totalPages = Math.ceil($pagination.count / $pagination.perPage);

  const prevPage = () => {
    console.log($pagination.page > 0, $pagination.page);
    if ($pagination.page > 0) {
      //pagination.update( x => ({...x, page: p}));
      toPage($pagination.page -1);
    }
  }

  const nextPage = () => {
    if ($pagination.page < totalPages - 1) {
      let p = $pagination.page + 1;
      //pagination.update( x => ({...x, page: p}));
      toPage($pagination.page + 1);
    }
  }

  const toPage = (p) => {
    pagination.update( x => ({...x, page: p}));
    toPageCallback([
      (p*$pagination.perPage),
      ((p+1)*$pagination.perPage)
    ]);
  }
</script>

<!-- {$pagination.page}/{totalPages} -->
<!-- ref: Melt UI -->
<ul class="uk-pagination uk-flex-center" uk-margin>
  <li><a href="#" on:click|preventDefault={prevPage}><span uk-pagination-previous></span></a></li>
  {#if totalPages <= 5}
    <!-- 5以下: 一般-->
    {#each Array(totalPages) as _, i}
      <li class={($pagination.page === i) ? "uk-active" : ""}><a href="#" on:click|preventDefault={() => toPage(i)}>{i+1}</a></li>
    {/each}
  {:else}
    <!-- 5以上前4後4中3 -->
    {#if $pagination.page < 3}
      {#each Array(3) as _, i}
        <li class={($pagination.page === i) ? "uk-active" : ""}><a href="#" on:click|preventDefault={()=>toPage(i)}>{i+1}</a></li>
      {/each}
      <li class={($pagination.page === 3) ? "uk-active" : ""}><a href="#" on:click|preventDefault={()=>toPage(3)}>4</a></li>
      <li class="uk-disabled"><span>…</span></li>
      <li><a href="#" on:click|preventDefault={()=>toPage(totalPages-1)}>{totalPages}</a></li>
    {:else}
      <li class={($pagination.page === 0) ? "uk-active" : ""}><a href="#" on:click|preventDefault={()=>toPage(0)}>1</a></li>
      <li class="uk-disabled"><span>…</span></li>
      {#if $pagination.page >= 3 && $pagination.page <= totalPages -3}
        <li><a href="#" on:click|preventDefault={()=>toPage($pagination.page - 1)}>{$pagination.page}</a></li>
        <li class="uk-active"><a href="#" on:click|preventDefault={()=>toPage($pagination.page)}>{$pagination.page+1}</a></li>
        <li><a href="#" on:click|preventDefault={()=>toPage($pagination.page+1)}>{$pagination.page+2}</a></li>
        <li class="uk-disabled"><span>…</span></li>
      {/if}
      {#if $pagination.page >= totalPages - 4 }
        <li class={($pagination.page === totalPages - 4) ? "uk-active" : ""}><a href="#" on:click|preventDefault={()=>toPage(totalPages - 4)}>{totalPages - 3}</a></li>
        <li class={($pagination.page === totalPages - 3) ? "uk-active" : ""}><a href="#" on:click|preventDefault={()=>toPage(totalPages - 3)}>{totalPages - 2}</a></li>
        <li class={($pagination.page === totalPages - 2) ? "uk-active" : ""}><a href="#" on:click|preventDefault={()=>toPage(totalPages - 2)}> {totalPages - 1}</a></li>
      {/if}
      <li class={($pagination.page === totalPages - 1) ? "uk-active" : ""}><a href="#" on:click|preventDefault={()=>toPage(totalPages - 1)}>{totalPages}</a></li>
    {/if}
  {/if}
  <li><a href="#" on:click|preventDefault={nextPage}><span uk-pagination-next></span></a></li>
</ul>
