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
    if ('defaultNamedAreas' in action) {
      newState = {
        ...newState,
        defaultNamedAreas: action.defaultNamedAreas,
      };
    }
    if ('value' in action && action.value) {
      newState = {
        ...newState,
        values: {
          ...newState.values,
          [action.value.area_class.name]: action.value,
        }
      };
    }
    return newState;
  case 'SET_BY_LONLAT':
    let newStateValues = {};
    if ('values' in action && action.values.length > 0) {
      for (const k in action.values) {
        newStateValues[action.values[k].area_class.name] = action.values[k];
      }
    }
    return {
      ...state,
      values: newStateValues,
      isFromLonLat: true
    };
  case 'SET_BY_SELECT':
    return {
      ...state,
      values: {},
      isFromLonLat: false
    };
  case 'DELETE_VALUE':
    delete state.values[action.key];
    return state;
  default:
    console.log('default');
  }
}

export default function GazetterSelector({recordId}) {

  const initState = {
    areaClasses: [],
    values: {},
    isFromLonLat: false,
  };

  const [state, dispatch] = useReducer(reducer, initState);
  let namedAreaIds = [];
  let displayText = {
    AList: [],
    LList: [],
  };

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
      const defaultNamedAreas = await fetch(`/api/v1/record/${recordId}/named-areas`)
            .then( resp => resp.json())
            .then( results => {
              return results;
            });

      dispatch({type: 'SET_DATA', areaClasses: areaClasses, defaultNamedAreas: defaultNamedAreas});
    };
    init();
  }, []);

  const handleAreaClassChange = (e, index) => {
    if (index < state.areaClasses.length) {
      let selectedId = e.target.value;
      if (!selectedId) {
        dispatch({type: 'DELETE_VALUE', key: state.areaClasses[index].name})
      }
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
  const handleFromSelect = (e) => {
    e.preventDefault();
    dispatch({type: 'SET_BY_SELECT'});
  };
  const handleFromLonLat = (e) => {
    e.preventDefault();
    const lat = document.getElementById('latitude-decimal');
    const lon = document.getElementById('longitude-decimal');
    if (lon && lon.value && lat && lat.value) {
      const ft = JSON.stringify({
        within: {
          srid: 4326,
          point: [lon.value, lat.value],
        }
      });
      fetch(`/api/v1/named-areas?filter=${ft}`)
        .then( resp => resp.json())
        .then( results => {
          dispatch({type: 'SET_BY_LONLAT', values: results.data});
        });
    }
  };

  const renderSelectors = (areaClasses) => {
    return areaClasses.map( (areaClass, index) => {
      //console.log((state.values && state.values[areaClass[index]] && state.values.areaClass[index]) ? state.values.areaClass[index]: null});
      return (
        <div className="uk-margin" key={index}>
          <label className="uk-form-label">{areaClass.label}</label>
          <div className="uk-form-controls">
            <select className="uk-select" id={`named_areas__${areaClass.name}`} onChange={(e) => handleAreaClassChange(e, index) } name={`named_areas__${areaClass.id}`} value={(state.values && state.values[areaClass[index]] && state.values.areaClass[index]) ? state.values.areaClass[index]: null}>
              {(areaClass.items.length > 0) ? <option value="">-- choose --</option> : null}
              {areaClass.items.map( x => {
                return (<option value={x.id} key={x.id}>{x.display_name}</option>);
              })}
            </select>
          </div>
        </div>
      );
    });
  };

  const LeftSide = () => {
    if (state.defaultNamedAreas
        && state.defaultNamedAreas.default
        && state.defaultNamedAreas.default.length) {
      const display = state.defaultNamedAreas.default.map( x => (x.display_name)).join(', ');
      return (
        <>
          <button className="uk-button" onClick={(e) => {
            e.preventDefault();
            dispatch({type: 'SET_DATA', defaultNamedAreas: state.defaultNamedAreas.default});
          }}>更改</button>
          <div className="uk-text">{display}</div>
        </>
      );
    } else {
      return (
        <>
          <div className="uk-text-lead">地名選擇</div>
          <div>
            <div className="uk-button-group">
              <button className={`uk-button ${state.isFromLonLat ? '' : 'uk-button-primary'}`} onClick={handleFromSelect}>使用地名選單</button>
              <button className={`uk-button ${state.isFromLonLat ? 'uk-button-primary' : ''}`} onClick={handleFromLonLat}>從經緯度取得</button>
            </div>
          </div>
          {(state.isFromLonLat) ? '' : renderSelectors(state.areaClasses) }
          <input className="uk-hidden" defaultValue={namedAreaIds} name="named_area_ids" />
        </>);
    }
  };

  // 整理
  // A: admininistrative, L: areas, parks
  for (let i in state.areaClasses) {
    const key = state.areaClasses[i].name;
    if (state.values[key]) {
      if (key === 'COUNTRY') {
        displayText.AList.push(state.values[key].display_name);
      } else if (key.slice(0,3) === 'ADM') {
        if ( key in state.values) {
          displayText.AList.push(state.values[key].display_name);
        }
      } else {
        displayText.LList.push([state.areaClasses[i].label, state.values[key].display_name]);
      }
    }
  };

  for (let k in state.values) {
    namedAreaIds.push(state.values[k].id);
  }

  // debug
  console.log('Gazetter state', state);
  console.log(displayText);

  return (
    <>
      <div>
        <LeftSide />
      </div>
      <div>
        <div className="uk-text-lead">標籤呈現</div>
        <dl className="uk-description-list">
          {(displayText.AList.length > 0) ? <><dt>行政區域</dt><dd>{displayText.AList.join(', ')}</dd></> : null}
          {(displayText.LList.length > 0) ? <><dt>其他地點名稱</dt><dd>{displayText.LList.map( x => (`${x[0]}: ${x[1]}`)).join(',')}</dd></> : null}
        </dl>
      </div>
    </>
  );
}
