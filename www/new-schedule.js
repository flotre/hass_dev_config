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
          hass: {},
          _config: {},
          _uncheckedItems: [],
          _checkedItems: []
        };
      }
  
  
    getCardSize() {
      return (this._config ? (this._config.title ? 1 : 0) : 0) + 3;
    }
  
    setConfig(config) {
      this._config = config;
      this._uncheckedItems = [];
      this._checkedItems = [];
      this._hours = [];
      this._weekdays = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
      /*for(var i=0; i<=24*60; i+=30) {
          this._hours.push(this._pad(Math.floor(i/60))+":"+this._pad(((i/30)%2)*30));
      }
      console.log(this._hours);*/
      for(var i=0; i<=24; i+=0.5) {
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
            <div class="row">
                <div class="entete">Heures</div>
                <div class="row">
                    ${repeat(this._hours, (item) => item,
                        (item, index) =>
                        html`<div id="entete_${index}" class="item">${index%2==0 ? item : ''}</div>`
                        )}
                </div>
            </div>
            <div class="row">
                <div class="entete">Lundi</div>
                <div class="row">
                    ${repeat(this._hours, (item) => item,
                        (item, index) =>
                        html`<div id="${index}" class="item" style="background-color: lightblue;"
                                  @click=${this._onclick}
                                  @pointerdown=${this._onpointerdown}
                                  @pointerup=${this._onpointerup}
                                  >
                                  </div>`
                        )}
                </div>
            </div>
        </ha-card>
      `;
    }
  
    static get styles() {
      return css`
        .row {
            display: flex;
            flex-direction: row;
            width: 100%;
        }

        .item {
            width: calc(100% / 24);
            margin-right: 2px;
        }

        .entete {
            min-width: 4em;
        }
      `;
    }

    _onclick(ev) {
        console.log("on click", ev);
        if(ev) {
            ev.target.style.background = "#ff77ee";
        }
    }

    _onpointerdown(ev) {
        console.log("on pointerdown", ev);
    }
  
    _onpointerup(ev) {
        console.log("on pointerup", ev);
    }    
}
  

customElements.define("schedule-card", ScheduleCard);
