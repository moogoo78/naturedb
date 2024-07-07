(function() {
  'use strict';

  let form = document.getElementById('login-form');
  let loginSubmitButton = document.getElementById('login-submit-button');
  let loginErrorMsg = document.getElementById('login-error-msg');
  let loginErrorMsgContent = document.getElementById('login-error-msg-content');

  async function login() {
    let formData = new FormData(form);
    let myHeaders = new Headers();
    myHeaders.append('Content-Type', 'application/json');
    const response = await fetch('/admin/login', {
      method: 'post',
      body: JSON.stringify({
        username: formData.get('username'),
        passwd: formData.get('passwd')
      }),
      headers: myHeaders,
    });
    const result = await response.json();
    if (response.status === 401 && result.msg) {
      loginErrorMsg?.removeAttribute('hidden');
      loginErrorMsgContent.textContent = result.msg;
    } else {
      localStorage.setItem('jwt', result.access_token);
      window.location.replace("/admin");
    }
  };

  form.addEventListener('keyup', function (e) {
    if (e.key === 'Enter' || e.keyCode === 13) {
      login();
    }
  });

  loginSubmitButton.onclick = (e) => {
    e.preventDefault();
    login();
  };


})();
