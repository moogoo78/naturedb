(function() {
  'use strict';
  const entities = document.getElementsByClassName('entity');
  for (let i=0; i < entities.length; i++) {
    entities[i].onclick = (e) => {
      e.preventDefault();
      if (window.confirm('確定要移出清單？')) {
      fetch(`/admin/api/user-lists/${e.currentTarget.dataset.user_list_id}`)
        .then( resp => resp.json())
        .then( result => {
          window.location.replace('/admin/user-list');
        });
      }
    };
};
})();
