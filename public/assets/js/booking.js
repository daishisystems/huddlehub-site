/*
 * Term 4 booking. No framework or external script is required.
 * DOM contract: #timetable-days; #booking-form with named parent-name, phone,
 * email, message, children-and-groups and bot-field fields; #booking-children;
 * #add-child; #active-child-label; #booking-error; #booking-submit;
 * #booking-whatsapp; #booking-success; #booking-success-name;
 * #booking-success-phone; #booking-reset. Optional #booking-success-message,
 * #booking-local-receipt and #timetable-feedback show preview and error details.
 * Generated styling classes: booking-child, is-active, child-heading,
 * child-activate, child-remove, child-fields, child-field, child-name, child-age,
 * group-options, group-option, group-selected, group-selection-marker,
 * timetable-day, timetable-slot, timetable-groups, timetable-group, sport-dot,
 * group-copy, group-new and group-pill. Selection buttons use native keyboard interaction
 * and aria-pressed. User values are always rendered with textContent.
 */
(function (global) {
  'use strict';

  const GROUPS = Object.freeze([
    { id: 'tue1-hk', day: 'Tue', time: '14:30–15:30', sport: 'Hockey', who: 'Mixed', ages: 'U7 & U9', dot: 'var(--teal)' },
    { id: 'tue1-nb', day: 'Tue', time: '14:30–15:30', sport: 'Netball', who: 'Girls', ages: 'U7 & U9', dot: 'var(--peach)' },
    { id: 'tue2-hk', day: 'Tue', time: '15:30–16:30', sport: 'Hockey', who: 'Mixed', ages: 'U11 & U13', dot: 'var(--teal)' },
    { id: 'tue2-nb', day: 'Tue', time: '15:30–16:30', sport: 'Netball', who: 'Girls', ages: 'U11 & U13', dot: 'var(--peach)' },
    { id: 'wed1-sc', day: 'Wed', time: '14:30–15:30', sport: 'Soccer', who: 'Girls', ages: 'All ages 6–13', dot: 'var(--orange)' },
    { id: 'wed2-rg', day: 'Wed', time: '15:30–16:30', sport: 'Rugby', who: 'Boys', ages: 'All ages 6–13', dot: 'var(--navy)' },
    { id: 'thu1-hk', day: 'Thu', time: '14:30–15:30', sport: 'Hockey', who: 'Mixed', ages: 'U7 & U9', dot: 'var(--teal)' },
    { id: 'thu1-pl', day: 'Thu', time: '14:30–15:30', sport: 'Performance Lab', who: '', ages: 'U7 & U9', dot: 'var(--lime)', isNew: true },
    { id: 'thu2-hk', day: 'Thu', time: '15:30–16:30', sport: 'Hockey', who: 'Mixed', ages: 'U11 & U13', dot: 'var(--teal)' },
    { id: 'thu2-pl', day: 'Thu', time: '15:30–16:30', sport: 'Performance Lab', who: '', ages: 'U11 & U13', dot: 'var(--lime)', isNew: true },
    { id: 'fri1-sc', day: 'Fri', time: '14:30–15:30', sport: 'Soccer', who: 'Boys', ages: 'U7 & U9', dot: 'var(--orange)' },
    { id: 'fri2-sc', day: 'Fri', time: '15:30–16:30', sport: 'Soccer', who: 'Boys', ages: 'U11 & U13', dot: 'var(--orange)' }
  ].map(Object.freeze));
  const DAYS = Object.freeze([
    ['Tue', 'Tuesday'], ['Wed', 'Wednesday', 'Age groups on the day'],
    ['Thu', 'Thursday'], ['Fri', 'Friday']
  ].map(Object.freeze));
  const groupsById = new Map(GROUPS.map(function (group) { return [group.id, group]; }));

  function fullDay(day) {
    const entry = DAYS.find(function (item) { return item[0] === day; });
    return entry ? entry[1] : day;
  }

  function groupLabel(group) {
    return group.sport + (group.who ? ' · ' + group.who : '') + ' · ' + group.ages;
  }

  function normalizePhone(value) {
    const compact = String(value || '').trim().replace(/[\s().-]/g, '');
    let digits;
    if (/^0[1-8]\d{8}$/.test(compact)) digits = compact.slice(1);
    else if (/^\+27[1-8]\d{8}$/.test(compact)) digits = compact.slice(3);
    else if (/^0027[1-8]\d{8}$/.test(compact)) digits = compact.slice(4);
    else if (/^27[1-8]\d{8}$/.test(compact)) digits = compact.slice(2);
    else return null;
    return '+27' + digits;
  }

  function timeRange(time) {
    const parts = String(time).split(/[–-]/);
    if (parts.length !== 2) return null;
    const minutes = parts.map(function (part) {
      const match = part.trim().match(/^(\d{1,2}):(\d{2})$/);
      if (!match || Number(match[1]) > 23 || Number(match[2]) > 59) return NaN;
      return Number(match[1]) * 60 + Number(match[2]);
    });
    return minutes.every(Number.isFinite) && minutes[0] < minutes[1] ? minutes : null;
  }

  function groupsOverlap(first, second) {
    if (!first || !second || first.day !== second.day) return false;
    const a = timeRange(first.time);
    const b = timeRange(second.time);
    return !!a && !!b && a[0] < b[1] && b[0] < a[1];
  }

  function findConflict(selectedIds, candidateId) {
    const candidate = groupsById.get(candidateId);
    return (selectedIds || []).map(function (id) { return groupsById.get(id); })
      .find(function (group) { return group && group.id !== candidateId && groupsOverlap(group, candidate); }) || null;
  }

  function toggleSelection(selectedIds, candidateId) {
    const current = (selectedIds || []).slice();
    if (!groupsById.has(candidateId)) return { groups: current, error: 'Please choose a group from the timetable.' };
    if (current.includes(candidateId)) return { groups: current.filter(function (id) { return id !== candidateId; }), error: '' };
    const conflict = findConflict(current, candidateId);
    if (conflict) {
      return { groups: current, error: 'These groups overlap on ' + fullDay(conflict.day) + ' at ' + conflict.time + '. Remove ' + conflict.sport + ' first, or choose another time.' };
    }
    return { groups: current.concat(candidateId), error: '' };
  }

  function childLabel(child, index) {
    return String(child.name || '').trim().split(/\s+/)[0] || 'Child ' + (index + 1);
  }

  function validateBooking(booking) {
    if (!String(booking.parent || '').trim()) return { field: 'parent-name', message: 'Please add your name.' };
    if (!normalizePhone(booking.phone)) return { field: 'phone', message: 'Please add a valid South African WhatsApp number, for example 076 824 3254 or +27 76 824 3254.' };
    const email = String(booking.email || '').trim();
    if (email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { field: 'email', message: 'Please check your email address, or leave it blank.' };
    if (!Array.isArray(booking.children) || !booking.children.length) return { field: 'children', message: 'Please add at least one child.' };
    for (let index = 0; index < booking.children.length; index += 1) {
      const child = booking.children[index];
      if (!String(child.name || '').trim()) return { field: 'name', childIndex: index, message: "Please add Child " + (index + 1) + "'s name." };
      const age = String(child.age || '').trim();
      if (!/^\d+$/.test(age) || Number(age) < 6 || Number(age) > 13) return { field: 'age', childIndex: index, message: 'Please add an age from 6 to 13 for ' + childLabel(child, index) + '.' };
      if (!Array.isArray(child.groups) || !child.groups.length) return { field: 'groups', childIndex: index, message: 'Please choose at least one group for ' + childLabel(child, index) + '.' };
      const accepted = [];
      for (const id of child.groups) {
        if (!groupsById.has(id)) return { field: 'groups', childIndex: index, message: 'Please choose a listed group for ' + childLabel(child, index) + '.' };
        if (findConflict(accepted, id)) return { field: 'groups', childIndex: index, message: childLabel(child, index) + ' has groups at the same time. Please remove one of them.' };
        if (!accepted.includes(id)) accepted.push(id);
      }
    }
    return null;
  }

  function summarizeChildren(children) {
    return children.map(function (child, index) {
      const name = String(child.name || '').trim() || 'Child ' + (index + 1);
      const age = String(child.age || '').trim();
      const lines = (child.groups || []).map(function (id) {
        const group = groupsById.get(id);
        return group ? '  - ' + group.day + ' ' + group.time + ' ' + group.sport + (group.who ? ' ' + group.who : '') + ' (' + group.ages + ')' : '';
      }).filter(Boolean);
      return name + (age ? ', age ' + age : '') + '\n' + (lines.join('\n') || '  - (no group selected)');
    }).join('\n\n');
  }

  function bookingPayload(booking, formName, honeypot) {
    return new URLSearchParams({
      'form-name': formName || 'term4-registration',
      'parent-name': String(booking.parent || '').trim(),
      phone: normalizePhone(booking.phone) || String(booking.phone || '').trim(),
      email: String(booking.email || '').trim(),
      'children-and-groups': summarizeChildren(booking.children),
      message: String(booking.message || '').trim(),
      'bot-field': String(honeypot || '')
    });
  }

  function whatsappUrl(booking) {
    const message = "Hi Juliette, I'd like to book Term 4 at HuddleHub.\n\nParent: " + String(booking.parent || '').trim()
      + '\nPhone: ' + String(booking.phone || '').trim() + '\nEmail: ' + String(booking.email || '').trim()
      + '\n\n' + summarizeChildren(booking.children)
      + (String(booking.message || '').trim() ? '\n\nNotes: ' + String(booking.message).trim() : '');
    return 'https://wa.me/27768243254?text=' + encodeURIComponent(message);
  }

  function isLocalHostname(hostname) {
    return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1' || hostname === '[::1]';
  }

  function init(document) {
    const form = document.getElementById('booking-form');
    const timetable = document.getElementById('timetable-days');
    const childrenContainer = document.getElementById('booking-children');
    if (!form || !timetable || !childrenContainer || form.dataset.bookingReady) return;
    form.dataset.bookingReady = 'true';
    form.noValidate = true;

    const addButton = document.getElementById('add-child');
    const activeLabel = document.getElementById('active-child-label');
    const errorBox = document.getElementById('booking-error');
    const timetableFeedback = document.getElementById('timetable-feedback');
    const submitButton = document.getElementById('booking-submit');
    const whatsapp = document.getElementById('booking-whatsapp');
    const success = document.getElementById('booking-success');
    const successName = document.getElementById('booking-success-name');
    const successPhone = document.getElementById('booking-success-phone');
    const successMessage = document.getElementById('booking-success-message');
    const paymentNextSteps = success.querySelector('p:not(#booking-success-message)');
    const resetButton = document.getElementById('booking-reset');
    const local = isLocalHostname(global.location.hostname);
    const originalSubmitLabel = submitButton.textContent;
    let sequence = 0;
    let children = [newChild()];
    let active = 0;
    let sending = false;
    let sent = false;
    let disabledControls = [];
    let previousWhatsappTabIndex = null;

    function newChild() {
      sequence += 1;
      return { id: sequence, name: '', age: '', groups: [] };
    }

    function element(tag, className, text) {
      const node = document.createElement(tag);
      if (className) node.className = className;
      if (text !== undefined) node.textContent = text;
      return node;
    }

    function namedValue(name) {
      const field = form.elements.namedItem(name);
      return field ? field.value : '';
    }

    function readBooking() {
      children.forEach(function (child) {
        const name = document.getElementById('child-' + child.id + '-name');
        const age = document.getElementById('child-' + child.id + '-age');
        if (name) child.name = name.value;
        if (age) child.age = age.value;
      });
      return { parent: namedValue('parent-name'), phone: namedValue('phone'), email: namedValue('email'), message: namedValue('message'), children: children };
    }

    function showError(message, inTimetable) {
      errorBox.textContent = message;
      errorBox.hidden = !message;
      if (timetableFeedback) {
        timetableFeedback.textContent = inTimetable ? message : '';
        timetableFeedback.hidden = !(inTimetable && message);
      }
    }

    function setActive(index) {
      active = Math.max(0, Math.min(index, children.length - 1));
      childrenContainer.querySelectorAll('.booking-child').forEach(function (card, i) {
        card.classList.toggle('is-active', i === active);
        const activate = card.querySelector('.child-activate');
        if (activate) activate.setAttribute('aria-pressed', String(i === active));
      });
      updateSelections();
      syncSummary();
    }

    function syncSummary() {
      const booking = readBooking();
      const summary = form.elements.namedItem('children-and-groups');
      if (summary) summary.value = summarizeChildren(booking.children);
      whatsapp.href = whatsappUrl(booking);
      activeLabel.textContent = children.length === 1 ? (children[0].name.trim() ? childLabel(children[0], 0) : 'your child') : childLabel(children[active], active);
      childrenContainer.querySelectorAll('.child-activate').forEach(function (button, index) {
        button.textContent = children.length === 1 ? 'Child' : childLabel(children[index], index);
        button.setAttribute('aria-label', 'Select groups for ' + childLabel(children[index], index));
      });
    }

    function selectGroup(index, id, inTimetable) {
      if (sending || sent) return;
      readBooking();
      active = index;
      const result = toggleSelection(children[index].groups, id);
      children[index].groups = result.groups;
      showError(result.error ? childLabel(children[index], index) + ': ' + result.error : '', inTimetable);
      setActive(index);
      syncSummary();
    }

    function groupButton(group, index, inTimetable) {
      const button = element('button', inTimetable ? 'timetable-group' : 'group-option');
      button.type = 'button';
      button.dataset.groupId = group.id;
      if (!inTimetable) button.dataset.childId = String(children[index].id);
      button.setAttribute('aria-pressed', 'false');
      button.setAttribute('aria-label', fullDay(group.day) + ' ' + group.time + ': ' + groupLabel(group));
      const dot = element('span', 'sport-dot');
      dot.style.background = group.dot;
      dot.setAttribute('aria-hidden', 'true');
      button.appendChild(dot);
      const copy = element('span', 'group-copy');
      const title = element('strong', '', group.sport + (group.who ? ' · ' + group.who : ''));
      if (group.isNew) { title.appendChild(document.createTextNode(' ')); title.appendChild(element('span', 'group-new', 'NEW')); }
      copy.appendChild(title);
      copy.appendChild(element('small', '', inTimetable ? group.ages : fullDay(group.day) + ' ' + group.time + ' · ' + group.ages));
      button.appendChild(copy);
      if (inTimetable) button.appendChild(element('span', 'group-pill', 'Add'));
      else {
        const marker = element('span', 'group-selection-marker', '');
        marker.setAttribute('aria-hidden', 'true');
        button.appendChild(marker);
      }
      button.addEventListener('click', function () { selectGroup(inTimetable ? active : index, group.id, inTimetable); });
      return button;
    }

    function renderTimetable() {
      timetable.replaceChildren();
      DAYS.forEach(function (day) {
        const dayCard = element('article', 'timetable-day');
        dayCard.appendChild(element('h3', '', day[1]));
        if (day[2]) dayCard.appendChild(element('p', '', day[2]));
        const dayGroups = GROUPS.filter(function (group) { return group.day === day[0]; });
        Array.from(new Set(dayGroups.map(function (group) { return group.time; }))).forEach(function (time) {
          const slot = element('div', 'timetable-slot');
          slot.appendChild(element('h4', '', time));
          const options = element('div', 'timetable-groups');
          dayGroups.filter(function (group) { return group.time === time; }).forEach(function (group) {
            options.appendChild(groupButton(group, 0, true));
          });
          slot.appendChild(options);
          dayCard.appendChild(slot);
        });
        timetable.appendChild(dayCard);
      });
    }

    function renderChildren() {
      childrenContainer.replaceChildren();
      children.forEach(function (child, index) {
        const card = element('fieldset', 'booking-child');
        card.dataset.childId = String(child.id);
        card.classList.toggle('is-active', index === active);
        const legend = element('legend', '', 'Child ' + (index + 1));
        card.appendChild(legend);
        const heading = element('div', 'child-heading');
        const activate = element('button', 'child-activate', childLabel(child, index));
        activate.type = 'button';
        activate.setAttribute('aria-pressed', String(index === active));
        activate.addEventListener('click', function () {
          if (sending || sent) return;
          setActive(index);
          syncSummary();
        });
        heading.appendChild(activate);
        if (children.length > 1) {
          const remove = element('button', 'child-remove', 'Remove child');
          remove.type = 'button';
          remove.setAttribute('aria-label', 'Remove Child ' + (index + 1));
          remove.addEventListener('click', function () {
            if (sending || sent) return;
            readBooking();
            const activeId = children[active].id;
            children.splice(index, 1);
            const nextActive = children.findIndex(function (remaining) { return remaining.id === activeId; });
            active = nextActive >= 0 ? nextActive : Math.min(index, children.length - 1);
            showError('');
            renderChildren();
            updateSelections();
            syncSummary();
            childrenContainer.querySelectorAll('.child-activate')[active].focus();
          });
          heading.appendChild(remove);
        }
        card.appendChild(heading);
        const fields = element('div', 'child-fields');
        [['name', "Child's name", 'text'], ['age', 'Age (6–13)', 'number']].forEach(function (entry) {
          const wrapper = element('div', 'child-field');
          const label = element('label', '', entry[1]);
          const input = element('input', 'child-' + entry[0]);
          input.id = 'child-' + child.id + '-' + entry[0];
          input.name = input.id;
          input.type = entry[2];
          input.required = true;
          input.value = child[entry[0]];
          label.htmlFor = input.id;
          if (entry[0] === 'name') { input.autocomplete = 'off'; input.maxLength = 120; }
          else { input.min = '6'; input.max = '13'; input.step = '1'; input.inputMode = 'numeric'; }
          input.addEventListener('focus', function () { setActive(index); });
          input.addEventListener('input', function () { child[entry[0]] = input.value; showError(''); syncSummary(); });
          wrapper.appendChild(label);
          wrapper.appendChild(input);
          fields.appendChild(wrapper);
        });
        card.appendChild(fields);
        card.appendChild(element('p', '', 'Choose groups for this child:'));
        const options = element('div', 'group-options');
        GROUPS.forEach(function (group) { options.appendChild(groupButton(group, index, false)); });
        card.appendChild(options);
        childrenContainer.appendChild(card);
      });
    }

    function updateSelections() {
      timetable.querySelectorAll('[data-group-id]').forEach(function (button) {
        const selected = children[active].groups.includes(button.dataset.groupId);
        button.setAttribute('aria-pressed', String(selected));
        button.classList.toggle('group-selected', selected);
        button.querySelector('.group-pill').textContent = selected ? 'Added' : 'Add';
      });
      childrenContainer.querySelectorAll('[data-group-id]').forEach(function (button) {
        const child = children.find(function (item) { return String(item.id) === button.dataset.childId; });
        const selected = child.groups.includes(button.dataset.groupId);
        button.setAttribute('aria-pressed', String(selected));
        button.classList.toggle('group-selected', selected);
        button.querySelector('.group-selection-marker').textContent = selected ? '✓' : '';
      });
    }

    function setSending(value) {
      sending = value;
      form.setAttribute('aria-busy', String(value));
      if (value) {
        const controls = Array.from(new Set(Array.from(form.querySelectorAll('input, button, select, textarea')).concat(Array.from(timetable.querySelectorAll('button')), [addButton])));
        disabledControls = controls.map(function (control) { return [control, control.disabled]; });
        disabledControls.forEach(function (entry) { entry[0].disabled = true; });
        previousWhatsappTabIndex = whatsapp.getAttribute('tabindex');
        whatsapp.setAttribute('aria-disabled', 'true');
        whatsapp.setAttribute('tabindex', '-1');
      } else {
        disabledControls.forEach(function (entry) { entry[0].disabled = entry[1]; });
        disabledControls = [];
        whatsapp.removeAttribute('aria-disabled');
        if (previousWhatsappTabIndex === null) whatsapp.removeAttribute('tabindex');
        else whatsapp.setAttribute('tabindex', previousWhatsappTabIndex);
      }
      submitButton.textContent = value ? 'Sending…' : originalSubmitLabel;
    }

    function focusInvalid(error) {
      if (error.childIndex !== undefined) {
        setActive(error.childIndex);
        syncSummary();
        const child = children[error.childIndex];
        const target = error.field === 'groups' ? childrenContainer.querySelectorAll('.booking-child')[error.childIndex].querySelector('.group-option') : document.getElementById('child-' + child.id + '-' + error.field);
        if (target) target.focus();
      } else {
        const field = form.elements.namedItem(error.field);
        if (field && typeof field.focus === 'function') field.focus();
      }
    }

    async function submit(event) {
      event.preventDefault();
      if (sending || sent) return;
      const booking = readBooking();
      syncSummary();
      const error = validateBooking(booking);
      if (error) { showError(error.message); focusInvalid(error); return; }
      const payload = bookingPayload(booking, form.name, namedValue('bot-field'));
      showError('');
      setSending(true);
      try {
        const response = await global.fetch('/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: payload.toString() });
        if (!response.ok) throw new Error('HTTP ' + response.status);
        if (local) {
          // A plain static server can return an HTML page without storing a form.
          // Require the local receiver's explicit receipt before claiming success.
          const receipt = await response.json();
          if (!receipt || receipt.localPreview !== true || receipt.ok !== true) throw new Error('Local form receiver did not confirm the submission');
        }
        sent = true;
        setSending(false);
        form.hidden = true;
        success.hidden = false;
        // Keep references to the original spans even after local-only copy replaces
        // their paragraph, so another submission after reset is safe.
        if (successName) successName.textContent = String(booking.parent).trim().split(/\s+/)[0];
        if (successPhone) successPhone.textContent = normalizePhone(booking.phone);
        if (successMessage) {
          if (local) successMessage.textContent = 'Local test complete. Your booking was saved only by this preview server. No real registration or notification was sent.';
          else if (successName && successPhone) successMessage.replaceChildren(document.createTextNode('Thanks, '), successName, document.createTextNode(". We'll send payment details to "), successPhone, document.createTextNode(' shortly, with the option to pay once or in 2 split payments. Payment secures your place.'));
        }
        const successHeading = success.querySelector('h3');
        if (successHeading) successHeading.textContent = local ? 'Local test saved ✓' : 'Booking sent 🎉';
        if (paymentNextSteps) paymentNextSteps.hidden = local;
        const receiptLink = document.getElementById('booking-local-receipt');
        if (receiptLink) {
          receiptLink.hidden = !local;
          if (local) { receiptLink.href = '/__preview/submissions'; receiptLink.textContent = 'Inspect the local test submission'; }
        }
        timetable.querySelectorAll('button').forEach(function (button) { button.disabled = true; });
        success.tabIndex = -1;
        success.focus();
        if (!local && typeof global.fbq === 'function') {
          try { global.fbq('track', 'Lead', { content_name: form.name }); } catch (_) { /* Tracking must not change a successful submission. */ }
        }
      } catch (_) {
        setSending(false);
        showError(local ? "That local test didn't save. Check that the preview server is running, then try again. No real booking has been sent." : "Sorry, your booking didn't send. Please try again, or use ‘Or send on WhatsApp’ below.");
        submitButton.focus();
      }
    }

    addButton.addEventListener('click', function () {
      if (sending || sent) return;
      readBooking();
      children.push(newChild());
      active = children.length - 1;
      showError('');
      renderChildren();
      updateSelections();
      syncSummary();
      document.getElementById('child-' + children[active].id + '-name').focus();
    });
    form.addEventListener('input', function () { if (!sending && !sent) { showError(''); syncSummary(); } });
    form.addEventListener('submit', submit);
    whatsapp.addEventListener('click', function (event) {
      if (sending) { event.preventDefault(); return; }
      syncSummary();
      const error = validateBooking(readBooking());
      if (error) { event.preventDefault(); showError(error.message); focusInvalid(error); }
    });
    resetButton.addEventListener('click', function () {
      if (sending) return;
      sent = false;
      form.reset();
      children = [newChild()];
      active = 0;
      form.hidden = false;
      success.hidden = true;
      const receiptLink = document.getElementById('booking-local-receipt');
      if (receiptLink) receiptLink.hidden = true;
      showError('');
      renderChildren();
      timetable.querySelectorAll('button').forEach(function (button) { button.disabled = false; });
      updateSelections();
      syncSummary();
      form.elements.namedItem('parent-name').focus();
    });
    renderTimetable();
    renderChildren();
    updateSelections();
    syncSummary();
  }

  const api = Object.freeze({ GROUPS: GROUPS, DAYS: DAYS, normalizePhone: normalizePhone, groupsOverlap: groupsOverlap, findConflict: findConflict, toggleSelection: toggleSelection, validateBooking: validateBooking, summarizeChildren: summarizeChildren, bookingPayload: bookingPayload, whatsappUrl: whatsappUrl, isLocalHostname: isLocalHostname, init: init });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (global) global.HuddleHubBooking = api;
  if (global && global.document) {
    if (global.document.readyState === 'loading') global.document.addEventListener('DOMContentLoaded', function () { init(global.document); });
    else init(global.document);
  }
})(typeof window !== 'undefined' ? window : globalThis);
