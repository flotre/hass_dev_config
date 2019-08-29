import {
    html,
    LitElement,
    css
  } from "https://unpkg.com/lit-element@2.0.1/lit-element.js?module";
import { repeat } from "https://unpkg.com/lit-html/directives/repeat.js?module";


const MODES_COLOR = {
    eco: 'lightblue',
    comfort: 'red',
    away: 'green'
};

  
class ScheduleCard extends LitElement {
  
    static getStubConfig() {
      return {};
    }
    static get properties() {
        return {
          schedule: {type: Array},
        };
    }

    constructor() {
        super();
        this._hours = [];
        this._weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        for(var i=0; i<24; i+=0.5) {
            this._hours.push(i);
        }
        this.schedule = Array(this._weekdays.length).fill(0).map(x => Array(this._hours.length).fill("eco"));
    }
  
  
    getCardSize() {
      return (this._config ? (this._config.title ? 1 : 0) : 0) + 3;
    }
  
    setConfig(config) {
      this._config = config;
      this._select_start = null;
      
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
                        html`<div id="${dindex}-${hindex}" class="item" style="background-color: ${MODES_COLOR[this.schedule[dindex][hindex]]};"
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
            <div>
                <label id="label2">Mode:</label>
                <paper-radio-group selected="${Object.keys(MODES_COLOR)[0]}" aria-labelledby="label2" @selected-changed="${this._modeSelected}">
                    ${Object.keys(MODES_COLOR).map(mode => html`
                    <paper-radio-button name="${mode}">${mode}</paper-radio-button>
                    `)}
                </paper-radio-group>
            </div>
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
        if(ev) {
            //ev.target.style.background = "#ff77ee";
            console.log("on click", ev.target);
            const id = ev.target.id;
            const iday = parseInt(id.split('-')[0], 10);
            const ihours = parseInt(id.split('-')[1], 10);
            console.log("on click", id, iday, ihours, this.schedule);
            // copy array
            const newschedule = [...this.schedule];
            newschedule[iday][ihours] = this.mode;
            console.log(newschedule);
            this.schedule = newschedule;
        }
    }

    _onpointerdown(ev) {
        //console.log("on pointerdown", ev);
        this._select_start = ev.target;
    }
  
    _onpointerup(ev) {
        //console.log("on pointerup", ev);
        this._select_start = null;
    }
    
    _onpointerenter(ev) {
        
        if( this._select_start ) {
            //ev.target.style.background = "#ff77ee";
        }
    }

    _modeSelected(ev) {
        this.mode = ev.target.selected;
        console.log("mode", ev.target, this.mode);
    }
}
  

customElements.define("schedule-card", ScheduleCard);
