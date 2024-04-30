const filterItems = (inputValue, options) => {
  if (!inputValue) {
    return [];
  }
  let filtered = [];
  if (inputValue) {
      options.forEach(option => {
        const text = option.text;
        const value = option.value;
        let isMatch = false;

        // 輸入一個字時，而且是英文，只檢查開頭
        if (inputValue.charCodeAt(0) > 127) {
          //第一個字unicode
          if (text.toLowerCase().includes(inputValue.toLowerCase())) {
            isMatch = true;
          }
        } else {
          if (inputValue.length === 1) {
            if (text.toLowerCase().startsWith(inputValue.toLowerCase())) {
              isMatch = true;
            }
          } else if (text.toLowerCase().includes(inputValue.toLowerCase())){
            isMatch = true;
          }
        }

        if (isMatch) {
	  filtered = [
            ...filtered,
            {
              styled: _makeMatchBold(text, inputValue),
              text: text,
              value: value,
            }
          ];
        }
      });
  }
  return filtered;
};

const _makeMatchBold = (str, inputValue) => {
  let start = str.toLowerCase().indexOf(inputValue.toLowerCase());
  let matched = str.substring(start, start+inputValue.length);
  let boldedMatch = str.replace(matched, `<strong>${matched}</strong>`);
  return boldedMatch;
};

const removeHTML = (str) => {
  //replace < and > all characters between
  return str.replace(/<(.)*?>/g, "");
  // return str.replace(/<(strong)>/g, "").replace(/<\/(strong)>/g, "");
};

const appendQuery = (paramsString, param, query) => {
  const searchParams = new URLSearchParams(paramsString);
  let tmp = {};
  for (const [key, value] of searchParams.entries()) {
    tmp[key] = JSON.parse(value);
    if (key === param) {
      tmp[key] = {...tmp[key], ...query};
    }
  }
  for (const key in tmp) {
    tmp[key] = JSON.stringify(tmp[key]);
  }
  return new URLSearchParams(tmp);
};

const fetchData = async (url) => {
  try {
    let response = await fetch(url);
    return await response.json();
  } catch(error) {
    console.error(`fetch error) ${error} | ${url}`);
    //  alert(error.message); // TODO
  }
};

const convertDDToDMS = (dd) => {
  /* arguments: decimal degree
   */
  const direction = (parseFloat(dd) >=0) ? 1 : -1;
  const ddFloat = Math.abs(parseFloat(dd));
  const degree = Math.floor(ddFloat);
  const minuteFloat = (ddFloat - degree) * 60;
  const minute = Math.floor(minuteFloat);
  const secondFloat = ((minuteFloat - minute) * 60);
  const second = parseFloat(secondFloat.toFixed(4));
    //console.log(dd, ddFloat,minuteFloat, [degree, minute, second]);
  return [direction, degree, minute, second];
};

const convertDMSToDD = (ddms) => {
  /* arguments: degree, minute, second
   */
  // console.log(ddms);
  return ddms[0] * (parseFloat(ddms[1]) + parseFloat(ddms[2]) / 60 + parseFloat(ddms[3]) / 3600);
};

export { filterItems, removeHTML, appendQuery, fetchData, convertDDToDMS, convertDMSToDD };
