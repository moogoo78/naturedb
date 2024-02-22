import React, { useState, useEffect, useReducer } from 'react';

function reducer(state, action) {
  switch (action.type) {
  case 'SET_DATA':
    let newState = { ...state };
    if ('areaClasses' in action) {
      newState = {
        ...newState,
        areaClasses: action.areaClasses,
      };
    }
    if ('value' in action) {
      newState = {
        ...newState,
        values: {
          ...newState.values,
          [action.value.area_class.name]: action.value.display_name,
        }
      };
    }
    return newState;
  default:
    console.log('default');
  }
}

export default function GazetterSelector() {
  const initState = {
    areaClasses: [],
    values: {},
  };

  const [state, dispatch] = useReducer(reducer, initState);

  useEffect( () => {
    async function init() {
      let preFetchList = [];
      let areaClasses = [];
      await fetch('/api/v1/area-classes')
            .then( resp => resp.json())
            .then( results => {
              for (const [index, data] of results.data.entries()) {
                areaClasses.push({
                  ...data,
                  items: [],
                });
                if (data.admin_config
                    && data.admin_config.myGazetter
                    && 'preFetch' in data.admin_config.myGazetter) {
                  preFetchList.push([index, data.id, data.admin_config.myGazetter.preFetch]);
                }
              };
            });

      // init fetch options
      for (let i in preFetchList) {
        const [index, areaClassId, conf] = preFetchList[i];
        let appendRange = '';
        if (conf.hasOwnProperty('range')) {
          appendRange = `&range=${JSON.stringify(conf.range)}`;
        }
        const data = await fetch(`/api/v1/named-areas?filter=${JSON.stringify({ area_class_id: areaClassId})}${appendRange}`)
              .then( resp => resp.json())
              .then( results => {
                return results.data;
              });
        areaClasses[index].items = data;
      };
      //console.log(areaClasses);
      dispatch({type: 'SET_DATA', areaClasses: areaClasses});
    };
    init();
  }, []);

  const handleAreaClassChange = (e, index) => {
    if (index < state.areaClasses.length) {
      let selectedId = e.target.value;
      const selectedItem = state.areaClasses[index].items.find( x => (parseInt(x.id) === parseInt(selectedId)));
      if (index + 1 === state.areaClasses.length) { // last one only update value
        dispatch({type: 'SET_DATA', value: selectedItem});
      } else if (state.areaClasses[index+1]
                 && state.areaClasses[index+1].parent_id) {
        let filter = JSON.stringify({
          area_class_id: state.areaClasses[index+1].id,
          parent_id: selectedId
        });
        fetch(`/api/v1/named-areas?filter=${filter}`)
          .then( resp => resp.json())
          .then( results => {
            let areaClasses = [...state.areaClasses];
            areaClasses[index+1].items = results.data;
            dispatch({type: 'SET_DATA', areaClasses: areaClasses, value: selectedItem});
          });
      } else {
        dispatch({type: 'SET_DATA', value: selectedItem});
      }
    }
  };

  // A: admininistrative, L: areas, parks
  let displayText = {
    AList: [],
    LList: [],
  };
  for (let i in state.areaClasses) {
    const key = state.areaClasses[i].name;
    if (state.values[key]) {
      if (key === 'COUNTRY') {
        displayText.AList.push(state.values[key]);
      } else if (key.slice(0,3) === 'ADM') {
        if ( key in state.values) {
          displayText.AList.push(state.values[key]);
        }
      } else {
        displayText.LList.push([state.areaClasses[i].label, state.values[key]]);
      }
    }
  };

  // debug
  console.log('Gazetter state', state);
  console.log(displayText);

  return (
    <>
      <div>
        <lead>地名選擇</lead>
        {state.areaClasses.map( (areaClass, index) => {
          return (
            <div className="uk-margin" key={index}>
              <label className="uk-form-label">{areaClass.label}</label>
              <div className="uk-form-controls">
                <select className="uk-select" id={"named_areas__"+areaClass.name} onChange={(e) => handleAreaClassChange(e, index) }>
                  {(areaClass.items.length > 0) ? <option value="">-- choose --</option> : null}
                  {areaClass.items.map( x => {
                    return (<option value={x.id} key={x.id}>{x.display_name}</option>);
                  })}
                </select>
              </div>
            </div>
          );
        })}
      </div>
      <div>
        <lead>標籤呈現</lead>
        <div className="uk-margin">
          <label className="uk-form-label">行政區域</label>
          <div className="uk-form-controls">
            <textarea className="uk-textarea" disabled value={displayText.AList.join(', ')}></textarea>
          </div>
        </div>
        <div className="uk-margin">
          <label className="uk-form-label">地名</label>
          <div className="uk-form-controls">
            <textarea className="uk-textarea" disabled value={displayText.LList.map( x => (`${x[0]}: ${x[1]}`)).join(',')}></textarea>
          </div>
        </div>
      </div>
    </>
  );
}
