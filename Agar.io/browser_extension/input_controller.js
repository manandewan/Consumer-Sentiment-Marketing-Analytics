// Input Controller module for Agar.io AI Bot with Global Event Getter Hooks
(function () {
  let aiTargetX = window.innerWidth / 2;
  let aiTargetY = window.innerHeight / 2;
  let isAiControlActive = true;

  // Intercept and override MouseEvent and PointerEvent prototype properties globally
  // This guarantees that any coordinates read by the game engine (regardless of event target or trust level) return AI targets.
  const setupOverrides = () => {
    const protoList = [MouseEvent.prototype, PointerEvent.prototype];
    
    protoList.forEach(proto => {
      // Helper to store original descriptors if not already done
      const overrideProp = (propName, getVal) => {
        const desc = Object.getOwnPropertyDescriptor(proto, propName);
        if (desc && desc.configurable) {
          Object.defineProperty(proto, propName, {
            get: function () {
              if (isAiControlActive) {
                return getVal(this);
              }
              return desc.get ? desc.get.call(this) : 0;
            },
            configurable: true
          });
        }
      };

      overrideProp('clientX', () => aiTargetX);
      overrideProp('clientY', () => aiTargetY);
      overrideProp('screenX', () => aiTargetX);
      overrideProp('screenY', () => aiTargetY);
      overrideProp('pageX', () => aiTargetX);
      overrideProp('pageY', () => aiTargetY);
      overrideProp('x', () => aiTargetX);
      overrideProp('y', () => aiTargetY);
      overrideProp('offsetX', () => aiTargetX);
      overrideProp('offsetY', () => aiTargetY);
    });
  };

  setupOverrides();

  // Dispatch both mousemove and pointermove events to trigger the game engine's internal listeners
  function dispatchAiEvents() {
    const canvas = document.getElementById('canvas') || document.querySelector('canvas') || window;

    const mouseEvt = new MouseEvent('mousemove', {
      clientX: aiTargetX,
      clientY: aiTargetY,
      bubbles: true,
      cancelable: true,
      view: window
    });
    mouseEvt.isAiSynthetic = true;

    const pointerEvt = new PointerEvent('pointermove', {
      clientX: aiTargetX,
      clientY: aiTargetY,
      bubbles: true,
      cancelable: true,
      view: window
    });
    pointerEvt.isAiSynthetic = true;

    canvas.dispatchEvent(mouseEvt);
    canvas.dispatchEvent(pointerEvt);
  }

  // Intercept user mouse movements to keep coordinates locked to the AI targets
  window.addEventListener('mousemove', function (e) {
    if (isAiControlActive && !e.isAiSynthetic) {
      e.stopImmediatePropagation();
      dispatchAiEvents();
    }
  }, true);

  window.addEventListener('pointermove', function (e) {
    if (isAiControlActive && !e.isAiSynthetic) {
      e.stopImmediatePropagation();
      dispatchAiEvents();
    }
  }, true);

  window.AgarioInputController = {
    executeAction: function (action) {
      if (!action || action.length < 4) return;

      const dx = action[0];
      const dy = action[1];
      const splitVal = action[2];
      const ejectVal = action[3];

      const centerX = window.innerWidth / 2;
      const centerY = window.innerHeight / 2;

      // Update AI target coordinate values
      aiTargetX = centerX + dx * 450;
      aiTargetY = centerY + dy * 450;

      // Force dispatch to update game engine's internal loop
      dispatchAiEvents();

      // Execute Split Action (Space key)
      if (splitVal > 0.5) {
        const spaceDown = new KeyboardEvent("keydown", { keyCode: 32, which: 32, code: "Space", key: " ", bubbles: true });
        const spaceUp = new KeyboardEvent("keyup", { keyCode: 32, which: 32, code: "Space", key: " ", bubbles: true });
        window.dispatchEvent(spaceDown);
        window.dispatchEvent(spaceUp);
      }

      // Execute Eject Mass Action (W key)
      if (ejectVal > 0.5) {
        const wDown = new KeyboardEvent("keydown", { keyCode: 87, which: 87, code: "KeyW", key: "w", bubbles: true });
        const wUp = new KeyboardEvent("keyup", { keyCode: 87, which: 87, code: "KeyW", key: "w", bubbles: true });
        window.dispatchEvent(wDown);
        window.dispatchEvent(wUp);
      }
    }
  };
})();
