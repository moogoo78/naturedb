(function() {
  "use strict";

  const passwordInput1 = document.getElementById('password-input1');
  const passwordInput2 = document.getElementById('password-input2');
  const submitButton = document.getElementById('submit-button');
  const form = document.getElementById('password-form');
  let isValidate = false;

  const validateOK = () => {
    isValidate = true;
    passwordInput1.classList.remove('uk-form-danger');
    passwordInput1.classList.add('uk-form-success');
    passwordInput2.classList.remove('uk-form-danger');
    passwordInput2.classList.add('uk-form-success');
  }

  passwordInput1.addEventListener('input', (e) => {
    if (e.target.value) {
      if (e.target.value === passwordInput2.value) {
        validateOK();
      } else {
        passwordInput1.classList.add('uk-form-danger');
        isValidate = false;
      }
    }
  });

  passwordInput2.addEventListener('input', (e) => {
    if (e.target.value) {
      if (e.target.value === passwordInput1.value) {
        validateOK();
      } else {
        passwordInput2.classList.add('uk-form-danger');
        isValidate = false;
      }
    }
  });

  submitButton.onclick = (e) => {
    e.preventDefault();
    if (isValidate) {
      form.submit();
    } else {
      alert('請確認密碼');
    }
  }
})();
