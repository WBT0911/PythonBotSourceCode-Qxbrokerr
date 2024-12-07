// ==UserScript==
// @name         wsHook qxbroker.com
// @namespace    Violentmonkey Scripts
// @version      0.1
// @description  Websocket Hook for qxbroker.com.
// @author       Yla Res
// @match        https://qxbroker.com/en/*
// @include      https://qxbroker.com/en/trade*
// @include      https://qxbroker.com/en/demo-trade*
/// @require      https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js
/// @require      https://cdnjs.cloudflare.com/ajax/libs/tesseract.js/4.1.1/tesseract.min.js
// @grant        none
// @run-at       document-start
// ==/UserScript==

var wsHook = {};

(function () {
  // Mutable MessageEvent.
  // Subclasses MessageEvent and makes data, origin and other MessageEvent properites mutatble.
  function MutableMessageEvent (o) {
    this.bubbles = o.bubbles || false
    this.cancelBubble = o.cancelBubble || false
    this.cancelable = o.cancelable || false
    this.currentTarget = o.currentTarget || null
    this.data = o.data || null
    this.defaultPrevented = o.defaultPrevented || false
    this.eventPhase = o.eventPhase || 0
    this.lastEventId = o.lastEventId || ''
    this.origin = o.origin || ''
    this.path = o.path || new Array(0)
    this.ports = o.parts || new Array(0)
    this.returnValue = o.returnValue || true
    this.source = o.source || null
    this.srcElement = o.srcElement || null
    this.target = o.target || null
    this.timeStamp = o.timeStamp || null
    this.type = o.type || 'message'
    this.__proto__ = o.__proto__ || MessageEvent.__proto__
  }

  var before = wsHook.before = function (data, url, wsObject) {
    return data
  }
  var after = wsHook.after = function (e, url, wsObject) {
    return e
  }
  var modifyUrl = wsHook.modifyUrl = function(url) {
    return url
  }
  wsHook.resetHooks = function () {
    wsHook.before = before
    wsHook.after = after
    wsHook.modifyUrl = modifyUrl
  }

  var _WS = WebSocket
  WebSocket = function (url, protocols) {
    var WSObject
    url = wsHook.modifyUrl(url) || url
    this.url = url
    this.protocols = protocols
    if (!this.protocols) { WSObject = new _WS(url) } else { WSObject = new _WS(url, protocols) }

    var _send = WSObject.send
    WSObject.send = function (data) {
      arguments[0] = wsHook.before(data, WSObject.url, WSObject) || data
      _send.apply(this, arguments)
    }

    // Events needs to be proxied and bubbled down.
    WSObject._addEventListener = WSObject.addEventListener
    WSObject.addEventListener = function () {
      var eventThis = this
      // if eventName is 'message'
      if (arguments[0] === 'message') {
        arguments[1] = (function (userFunc) {
          return function instrumentAddEventListener () {
            arguments[0] = wsHook.after(new MutableMessageEvent(arguments[0]), WSObject.url, WSObject)
            if (arguments[0] === null) return
            userFunc.apply(eventThis, arguments)
          }
        })(arguments[1])
      }
      return WSObject._addEventListener.apply(this, arguments)
    }

    Object.defineProperty(WSObject, 'onmessage', {
      'set': function () {
        var eventThis = this
        var userFunc = arguments[0]
        var onMessageHandler = function () {
          arguments[0] = wsHook.after(new MutableMessageEvent(arguments[0]), WSObject.url, WSObject)
          if (arguments[0] === null) return
          userFunc.apply(eventThis, arguments)
        }
        WSObject._addEventListener.apply(this, ['message', onMessageHandler, false])
      }
    })

    return WSObject
  }
WebSocket.CONNECTING = _WS.CONNECTING;
WebSocket.OPEN = _WS.OPEN;
WebSocket.CLOSING = _WS.CLOSING;
WebSocket.CLOSED = _WS.CLOSED;
})();

/*
 * Trick
 */

const _trade = {isRun: false};

const _TextDecoder = (data) => {return new TextDecoder('utf-8').decode(data);}

const _notifyBackend = async (event, messageToBackend, WSObject) => {

  messageFromBackend = (await window.notifyBackend?.(event, messageToBackend));

  if (messageFromBackend?.[0] == 'orders/open' && messageFromBackend[1]) {
    _trade.isRun = true;
    let asset = JSON.parse (messageFromBackend[1])[1]["asset"];
    WSObject.send (`42["instruments/update",{"asset":"${asset}","period":60}]`);
    WSObject.send (`42["chart_notification/get",{"asset":"${asset}","version":"1.0.0"}]`);
    WSObject.send (`42["depth/unfollow","${asset}"]`);
    WSObject.send (`42["depth/follow","${asset}"]`);
    WSObject.send (`42${messageFromBackend[1]}`);
  }
  else if (messageFromBackend?.[0] == 'window.close' && messageFromBackend[1]) {
    window.close();
  }
  else if (messageFromBackend?.[0] == 'console.log' && !messageFromBackend[1].includes('451-["quotes/stream",')) {
    console.log(messageFromBackend[1]);
  }
  else if (!messageToBackend.includes('451-["quotes/stream",')){
    console.log(`Message to send: ${messageToBackend}`);
  }
}

wsHook.before = function (data, url, WSObject) {
  _notifyBackend('↑', (data instanceof ArrayBuffer ? _TextDecoder(data) : data), WSObject);
  return data;
}

wsHook.after = function (messageEvent, url, WSObject) {
  _notifyBackend('↓', (messageEvent.data instanceof ArrayBuffer ? _TextDecoder(messageEvent.data) : messageEvent.data), WSObject);
  return messageEvent;
}
