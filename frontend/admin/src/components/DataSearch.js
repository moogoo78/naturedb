import React, { useState, useEffect, useReducer } from 'react';
import { useForm } from 'react-hook-form';


const onSubmit = (data) => console.log(data)

function reducer(state, action) {
  switch (action.type) {
  case 'SET_Q':
    return {
      ...state,
      q: action.value
    };
  }
};

const handleFullTextSearch = (e, dispatch) => {
  dispatch({type: 'SET_Q', value: e.target.value});
  };

const SearchBar = ({dispatch, state, register}) => {
    return (
      <div className="uk-child-width-expand uk-grid-small" uk-grid="">
        <div className="uk-width-expand">
          <div className="uk-inline uk-width-extand">
            <span className="uk-form-icon" uk-icon="icon: search"></span>
            <input id="data-search-searchbar-input" type="search" name="text_search" className="search-input uk-input uk-form-large" placeholder="全文搜尋" defaultValue="" {...register('q')} />
          </div>
          <div id="data-search-searchbar-dropdown" className="uk-width-2xlarge uk-margin-remove" hidden>
            <ul id="data-search-searchbar-dropdown-list" className="uk-list uk-list-divider uk-padding-remove-vertical">
            </ul>
          </div>
        </div>
        <div className="uk-width-auto">
          <button className="uk-button uk-button-primary uk-form-large" type="submit">送出</button>
        </div>
      </div>
    );
  };

export default function DataSearch() {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm();

  const initState = {
    view: 'table',
    q: '',
    ftsCategories: {},
  };
  const [state, dispatch] = useReducer(reducer, initState);


  return (
    <>
    <form onSubmit={handleSubmit(onSubmit)}>
      <SearchBar dispatch={dispatch} state={state} register={register}/>
      <a className="uk-button uk-button-default uk-margin" href="#modal-overflow" uk-toggle="">條件搜尋</a>
      <ul uk-tab="">
        <li><a href="#">學名</a></li>
        <li><a href="#">人名</a></li>
        <li><a href="#">地名</a></li>
        <li><a href="#">採集號</a></li>
        <li><a href="#">館號</a></li>
      </ul>
      <ul className="uk-switcher uk-margin">
        <li>


          <div className="uk-child-width-1-2@s" uk-grid="">
            <div>
              <div className="uk-card uk-card-hover uk-card-body uk-card-small uk-card-default">
                <h3 className="uk-card-title">Hover</h3>
                <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit.</p>
              </div>
            </div>
            <div>
        <div className="uk-card uk-card-hover uk-card-body uk-card-small">
          <h3 className="uk-card-title">Hover</h3>
          <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit.</p>
        </div>
            </div>
            <div>
        <div className="uk-card uk-card-hover uk-card-body">
            <h3 className="uk-card-title">Hover</h3>
          <p>Lorem ipsum dolor sit amet, consectetur adipisicing elit.</p>
        </div>
            </div>
          </div>

        </li>
        <li>Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.</li>
        <li>Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur, sed do eiusmod.</li>
    </ul>
    </form>
    </>
  );
};
