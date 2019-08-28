import {
    html,
    LitElement,
    css
  } from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";
import { repeat } from "https://unpkg.com/lit-html/directives/repeat.js?module";
  


  
class ScheduleCard extends LitElement {
  
    static getStubConfig() {
      return {};
    }
    static get properties() {
        return {
          myProp: {type: Number},
        };
    }

    constructor() {
        super();
        this.myProp = 1;
    }
  
  
    getCardSize() {
      return (this._config ? (this._config.title ? 1 : 0) : 0) + 3;
    }
  
    setConfig(config) {
      this._config = config;
      this._select_start = null;
      this._hours = [];
      this._weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
      /*for(var i=0; i<=24*60; i+=30) {
          this._hours.push(this._pad(Math.floor(i/60))+":"+this._pad(((i/30)%2)*30));
      }
      console.log(this._hours);*/
      for(var i=0; i<24; i+=0.5) {
        this._hours.push(i);
        }
    }

    _pad(d) {
        return (d < 10) ? '0' + d.toString() : d.toString();
    }
  
  
    render() {
      if (!this._config || !this.hass) {
        return html``;
      }
  
      return html`
        <ha-card .header="${this._config.title}">
            <div class="wrapper">
                
                <div class="entete_h"></div>
                
                ${repeat(this._hours, (item) => item,
                    (item, index) =>
                    html`${index%2==0 ? html`<div id="entete_${index}" class="item hours">${item}</div>` : ''}`
                )}
                
                ${repeat(this._weekdays, (item) => item,
                    (day, dindex) =>
                    html`<div class="entete">${day}</div>
                    ${repeat(this._hours, (item) => item,
                        (hour, hindex) =>
                        html`<div id="${dindex}-${hindex}" class="item" style="background-color: lightblue;"
                                @click="${this._onclick}"
                                @pointerdown="${this._onpointerdown}"
                                @pointerup="${this._onpointerup}"
                                @pointerenter="${this._onpointerenter}"
                                >
                                </div>`
                    )}
                    `
                )}
                
            </div>
            <paper-dropdown-menu label="Mode">
                <paper-listbox slot="dropdown-content" selected="${this.myProp}" @selected-changed="${this._modeSelected}">
                    <paper-item>eco</paper-item>
                    <paper-item>comfort</paper-item>
                    <paper-item>away</paper-item>
                </paper-listbox>
            </paper-dropdown-menu>
        </ha-card>
      `;
    }
  
    static get styles() {
      return css`
        .wrapper {
            display: grid;
            grid-template-columns: auto repeat(48, 1fr);
            grid-gap: 1px;
        }

        .hours {
            font-size: 10px;
            grid-column-start: span 2;
        }
    
      `;
    }

    _onclick(ev) {
        console.log("on click", ev, this.myProp);
        if(ev) {
            ev.target.style.background = "#ff77ee";
        }
    }

    _onpointerdown(ev) {
        console.log("on pointerdown", ev);
        this._select_start = ev.target;
    }
  
    _onpointerup(ev) {
        console.log("on pointerup", ev);
        this._select_start = null;
    }
    
    _onpointerenter(ev) {
        
        if( this._select_start ) {
            ev.target.style.background = "#ff77ee";
        }
    }

    _modeSelected(ev) {
        console.log("on _modeSelected", ev);
    }
}
  

customElements.define("schedule-card", ScheduleCard);
