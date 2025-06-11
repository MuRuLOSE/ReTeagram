$(document).ready(function() {
  var translations = {
    en: {
      "welcome_message": "Welcome to Teagram-v2. To start, press button below and follow instructions.",
      "welcome_button": "Get Started",
      "enter_tokens_title": "Enter API Tokens",
      "token_instruction1": "Visit the website <a href='https://my.telegram.org' target='_blank'>my.telegram.org</a>",
      "token_instruction2": "Go to 'API development tools'",
      "token_instruction3": "Copy your API ID and API HASH, and enter them in the fields above",
      "api_id_placeholder": "API ID",
      "api_hash_placeholder": "API HASH",
      "submit_tokens": "Submit Tokens",
      "qr_title": "Log in to Telegram by QR Code",
      "instruction1": "Open Telegram on your phone",
      "instruction2": "Go to Settings > Devices > Link Desktop Device",
      "instruction3": "Point your phone at this screen to confirm login",
      "login_by_phone": "LOG IN BY PHONE NUMBER",
      "lang_switch": "Switch to Russian",
      "phone_login_title": "Log in by Phone",
      "phone_number_placeholder": "Phone number",
      "submit_phone": "Submit Phone",
      "phone_code_placeholder": "Confirmation code",
      "submit_code": "Submit Code",
      "back_to_qr": "Back to QR Code",
      "two_factor_title": "Two-Factor Authentication",
      "password_placeholder": "Password",
      "submit_password": "Submit Password",
      "password_hint": "Hint: %s",
      "final_message": "Finished! Return to Telegram and wait for inline bot.",
      "set_password_title": "Set Password",
      "set_password_placeholder": "Enter new password",
      "set_password_button": "Set Password",
      "wrong_password": "Wrong password, please try again.",
      "password_required": "Password required to continue."
    },
    ru: {
      "welcome_message": "Добро пожаловать в Teagram-v2. Чтобы начать, нажмите кнопку ниже и следуйте инструкциям.",
      "welcome_button": "Начать",
      "enter_tokens_title": "Введите API токены",
      "token_instruction1": "Зайдите на сайт <a href='https://my.telegram.org' target='_blank'>my.telegram.org</a>",
      "token_instruction2": "Перейдите в раздел «API development tools»",
      "token_instruction3": "Скопируйте API ID и API HASH, и введите их в поля выше",
      "api_id_placeholder": "API ID",
      "api_hash_placeholder": "API HASH",
      "submit_tokens": "Подтвердить",
      "qr_title": "Войти в Telegram с помощью QR-кода",
      "instruction1": "Откройте Telegram на своем телефоне",
      "instruction2": "Перейдите в Настройки > Устройства > Привязать устройство",
      "instruction3": "Наведите камеру телефона на этот экран для подтверждения входа",
      "login_by_phone": "ВОЙТИ ПО НОМЕРУ ТЕЛЕФОНА",
      "lang_switch": "Switch to English",
      "phone_login_title": "Войти по телефону",
      "phone_number_placeholder": "Номер телефона",
      "submit_phone": "Отправить номер",
      "phone_code_placeholder": "Код подтверждения",
      "submit_code": "Подтвердить код",
      "back_to_qr": "Вернуться к QR-коду",
      "two_factor_title": "Двухфакторная аутентификация",
      "password_placeholder": "Пароль",
      "submit_password": "Подтвердить",
      "password_hint": "Подсказка: %s",
      "final_message": "Готово! Вернитесь в Telegram и ждите inline-бота.",
      "set_password_title": "Установите пароль",
      "set_password_placeholder": "Введите новый пароль",
      "set_password_button": "Установить пароль",
      "wrong_password": "Неверный пароль, попробуйте снова.",
      "password_required": "Для продолжения требуется пароль."
    }
  };

  var isMobile = /Mobi|Android/i.test(navigator.userAgent);
  var firstTranslation = false;
  var hasStarted = false;
  var currentLanguage = "en";
  var phoneAuthActive = false;
  var pendingMessages = [];

  function translatePage(animated) {
    animated = typeof animated !== 'undefined' ? animated : true;
    $('[data-key]').each(function() {
      var key = $(this).data('key');
      if (translations[currentLanguage][key]) {
        if (firstTranslation || !animated) {
          $(this).html(translations[currentLanguage][key]);
        } else {
          $(this).fadeOut(200, function() {
            $(this).html(translations[currentLanguage][key]).fadeIn(200);
          });
        }
      }
    });

    $('[data-placeholder-key]').each(function() {
      var key = $(this).data('placeholder-key');
      if (translations[currentLanguage][key]) {
        $(this).attr('placeholder', translations[currentLanguage][key]);
      }
    });

    $('[data-button-key]').each(function() {
      var key = $(this).data('button-key');
      if (translations[currentLanguage][key]) {
        if (firstTranslation || !animated) {
          $(this).html(translations[currentLanguage][key]);
        } else {
          $(this).fadeOut(200, function() {
            $(this).html(translations[currentLanguage][key]).fadeIn(200);
          });
        }
      }
    });
    firstTranslation = false;
  }

  translatePage(false);

  if (isMobile) {
    phoneAuthActive = true;
    showWindow("phone-section");
  }

  // --- Password UI ---
  function showPasswordWindow(type) {
    // type: "set" or "enter"
    $("#password-section, #set-password-section").remove(); // Remove if exists

    var html = "";
    if (type === "set") {
      html = `
        <div id="set-password-section" class="window active">
          <h2>${translations[currentLanguage]["set_password_title"]}</h2>
          <input type="password" id="set_password_input" class="form-control" placeholder="${translations[currentLanguage]["set_password_placeholder"]}">
          <button id="set-password-btn" class="btn btn-primary">${translations[currentLanguage]["set_password_button"]}</button>
          <div id="set-password-error" style="color:red;display:none;margin-top:10px;"></div>
        </div>
      `;
    } else {
      html = `
        <div id="password-section" class="window active">
          <h2>${translations[currentLanguage]["password_required"]}</h2>
          <input type="password" id="enter_password_input" class="form-control" placeholder="${translations[currentLanguage]["password_placeholder"]}">
          <button id="enter-password-btn" class="btn btn-primary">${translations[currentLanguage]["submit_password"]}</button>
          <div id="enter-password-error" style="color:red;display:none;margin-top:10px;"></div>
        </div>
      `;
    }
    $("#login-container").children(".window.active").removeClass("active").hide();
    $("#login-container").append(html);

    if (type === "set") {
      $("#set-password-btn").off("click").on("click", function() {
        var pwd = $("#set_password_input").val();
        if (!pwd) {
          $("#set-password-error").text(translations[currentLanguage]["password_required"]).show();
          return;
        }
        ws.send(JSON.stringify({type: "set_password", content: pwd}));
        $("#set-password-btn").prop("disabled", true);
      });
    } else {
      $(document).off("click", "#enter-password-btn");
      $(document).on("click", "#enter-password-btn", function() {
        var pwd = $("#enter_password_input").val();
        if (!pwd) {
          $("#enter-password-error").text(translations[currentLanguage]["password_required"]).show();
          return;
        }
        ws.send(JSON.stringify({type: "password", content: pwd}));
        $("#enter-password-btn").prop("disabled", true);
      });
    }
  }

  function processMessage(msg) {
    const $message = $("#message");
    function updateMessage(text) {
      $message.fadeOut(200, function() {
        $(this).text(text).fadeIn(200);
      });
    }
    switch (msg.type) {
      case "set_password":
        showPasswordWindow("set");
        break;
      case "password_required":
        showPasswordWindow("enter");
        break;
      case "wrong_password":
        $("#enter-password-error").text(translations[currentLanguage]["wrong_password"]).show();
        $("#enter-password-btn").prop("disabled", false);
        break;
      case "password_set":
        $("#set-password-section").fadeOut(200, function() {
          $(this).remove();
          showWindow("tokens-section");
        });
        break;
      case "enter_tokens":
        showWindow("tokens-section");
        updateMessage("");
        break;
      case "qr_login":
        if (phoneAuthActive) break;
        showWindow("qr-section");
        $("#qr-container").empty();
        const qrCode = new QRCodeStyling({
          width: 205,
          height: 205,
          type: "canvas",
          data: msg.content,
          image: "https://avatars.githubusercontent.com/u/6113871",
          dotsOptions: {
            color: "#ffffff",
            type: "extra-rounded",
          },
          backgroundOptions: {
            color: "transparent",
          },
          imageOptions: {
            hideBackgroundDots: true,
            crossOrigin: "anonymous",
          },
        });
        qrCode.append(document.getElementById("qr-container"));
        updateMessage("");
        break;
      case "session_password_needed":
        showTelegram2FAWindow(msg.hint);
        break;
      case "message":
        updateMessage(msg.content);
        if (msg.content && msg.content.toLowerCase().includes("cloud authentication successful")) {
          setTimeout(function() {
            ws.close(1000);
          }, 1000);
        }
        break;
      case "error":
        updateMessage(msg.content);
        break;
      default:
        console.log("Unknown message type:", msg);
    }
  }

  function processPendingMessages() {
    while (pendingMessages.length > 0) {
      var msg = pendingMessages.shift();
      processMessage(msg);
    }
  }

  $("#welcome-btn").click(function() {
    hasStarted = true;
    $("#welcome-section").fadeOut(500, function() {
      processPendingMessages();
    });
  });

  let wsUrl = window.location.protocol === "https:" ?
    "wss://" + window.location.host + "/ws" :
    "ws://" + window.location.host + "/ws";
  const ws = new WebSocket(wsUrl);

  ws.onopen = function() {
    console.log("WebSocket connected");
  };

  ws.onmessage = function(event) {
    const msg = JSON.parse(event.data);
    if (!hasStarted) {
      pendingMessages.push(msg);
      return;
    }
    processMessage(msg);
  };

  ws.onclose = function(event) {
    if (event.code === 1000) {
      $("#login-container").fadeOut("slow", function() {
        $("<p>", {
          text: translations[currentLanguage]["final_message"],
          class: "final-message"
        }).appendTo("body").hide().fadeIn("slow");
      });
    }
  };

  function showWindow(windowId) {
    var $target = $("#" + windowId);
    if (!$target.length) {
      console.warn("No such window:", windowId);
      return;
    }
    var $currentWindow = $(".window.active");
    if ($currentWindow.length) {
      $currentWindow.fadeOut(300, function() {
        $currentWindow.removeClass("active");
        $target.fadeIn(300, function() {
          $target.addClass("active");
        });
      });
    } else {
      $target.fadeIn(300, function() {
        $target.addClass("active");
      });
    }
  }

  $("#tokens-btn").click(function() {
    const api_id = $("#api_id").val();
    const api_hash = $("#api_hash").val();

    ws.send(JSON.stringify({
      type: "tokens",
      API_ID: api_id,
      API_HASH: api_hash
    }));

    showWindow("qr-section");
    $("#message").fadeOut(200, function() {
      $(this).empty().fadeIn(200);
    });
  });

  $("#to-phone").click(function(e) {
    e.preventDefault();
    phoneAuthActive = true;
    showWindow("phone-section");
    $("#message").empty();
  });

  $("#to-qr").click(function(e) {
    e.preventDefault();
    phoneAuthActive = false;
    showWindow("qr-section");
    $("#message").empty();
  });

  $("#phone-number-btn").click(function() {
    const phone_number = $("#phone_number").val();
    ws.send(JSON.stringify({
      type: "phone_number",
      phone_number: phone_number
    }));
    $("#phone-step1").fadeOut("fast", function() {
      $("#phone-step2").fadeIn("fast");
    });
  });

  $("#phone-code-btn").click(function() {
    const phone_code = $("#phone_code").val();
    ws.send(JSON.stringify({
      type: "phone_code",
      phone_code: phone_code
    }));
  });

  $("#password-btn").click(function() {
    const password = $("#login_password").val();
    ws.send(JSON.stringify({
      type: "cloud_auth",
      password: password
    }));
  });

  $("#lang-switch").click(function(e) {
    e.preventDefault();
    currentLanguage = (currentLanguage === "en") ? "ru" : "en";
    translatePage(true);
  });

  $("#qr-container").on("click", function() {
    ws.send(JSON.stringify({ type: "authorize_qr" }));
  });

  var greetings = [
    "Hello!", "Привет!", "Hola!", "Bonjour!", "Ciao!", "Hallo!", "Olá!", "Hej!", "Ahoj!", "Szia!",
    "Salam!", "Namaste!", "Konnichiwa!", "Annyeong!", "Merhaba!", "Yassas!", "Shalom!",
    "Salue!", "Sveiki!", "Dobrý den!", "Tere!", "Xin chào!", "Selam!", "Mabuhay!", "Sawadee!",
    "Jambo!", "Habari!", "Bula!", "Kamusta!", "Sawatdee!", "God dag!", "Moien!", "Halo!", "Cześć!"
  ];

  function typeEffect(element, text, callback) {
    var index = 0;
    var interval = setInterval(function() {
      $(element).append(text[index]);
      index++;
      if (index === text.length) {
        clearInterval(interval);
        if (callback) setTimeout(callback, 1000);
      }
    }, 100);
  }

  function deleteEffect(element, callback) {
    var text = $(element).text();
    var interval = setInterval(function() {
      text = text.slice(0, -1);
      $(element).text(text);
      if (text.length === 0) {
        clearInterval(interval);
        $(element).html('&nbsp;');
        if (callback) callback();
      }
    }, 50);
  }

  function cycleGreetings(greetingsArr, index) {
    var element = document.querySelector('h1[data-key="welcome_title"]');
    if (!element) return;
    typeEffect(element, greetingsArr[index], function() {
      setTimeout(function() {
        deleteEffect(element, function() {
          var nextIndex = (index + 1) % greetingsArr.length;
          cycleGreetings(greetingsArr, nextIndex);
        });
      }, 1000);
    });
  }

  cycleGreetings(greetings, 0);

  function showTelegram2FAWindow(hint) {
    $("#telegram-2fa-section").remove();
    var html = `
      <div id="telegram-2fa-section" class="window active">
        <h2>${translations[currentLanguage]["two_factor_title"]}</h2>
        <input type="password" id="telegram_2fa_input" class="form-control" placeholder="${translations[currentLanguage]["password_placeholder"]}">
        <div id="telegram-2fa-hint" style="margin:10px 0;color:#888;">${hint ? translations[currentLanguage]["password_hint"].replace('%s', hint) : ''}</div>
        <button id="telegram-2fa-btn" class="btn btn-primary">${translations[currentLanguage]["submit_password"]}</button>
        <div id="telegram-2fa-error" style="color:red;display:none;margin-top:10px;"></div>
      </div>
    `;
    $("#login-container").children(".window.active").removeClass("active").hide();
    $("#login-container").append(html);

    $(document).off("click", "#telegram-2fa-btn");
    $(document).on("click", "#telegram-2fa-btn", function() {
      var pwd = $("#telegram_2fa_input").val();
      if (!pwd) {
        $("#telegram-2fa-error").text(translations[currentLanguage]["password_required"]).show();
        return;
      }
      ws.send(JSON.stringify({type: "cloud_auth", password: pwd}));
      $("#telegram-2fa-btn").prop("disabled", true);
    });
  }

});