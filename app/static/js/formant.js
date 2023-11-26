const  Formant = (()=> {
  const m = {};
  let data = {};
  let formElement = null;
  m.register = (formId, entities) => {
    formElement = document.getElementById(formId);
    data = new FormData(formElement);
  };
  m.data = data;
  m.getFormData = () => { return data };
  return m;
})();

export default Formant;


