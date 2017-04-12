Vue.component('confirmpublicaccess', {
  template: '#modal-template',
  props: ['show']
})
Vue.component('confirmdirectaccess', {
  template: '#modal-template',
  props: ['show']
})
var accessgrant = new Vue ({
  el:'#access-grant',
  data: {
    token: readCookie('token'),
    read: permissions.read,
    interact: permissions.interact,
    fork: permissions.fork,
    show_modal_direct_access_grant: false,
    show_modal_public_permissions_change: false
  },
  watch: {
    read: function() {
      if (!this.read) this.interact = false
    },
    interact: function() {
      if (this.interact) this.read = true
      else this.fork = false
    },
    fork: function() {
      if (this.fork) this.interact = true
    }
  },
  methods: {
    begin_direct_access: function() {
      this.show_modal_direct_access_grant = true
    },
    begin_public_permissions: function() {
      this.show_modal_public_permissions_change = true
    },
    grantAccess: function() {
      var headers = {
        'Auth-Token': this.token
      }
      var access = {'read':this.read, 'interact':this.interact, 'fork':this.fork}
      var api_str = '/api/accessreqs/'+request_id+'/grantaccess'
      this.$http.put(api_str, access, {headers: headers}).then((response) => {
        if (response.status == 200 || response.status == 201)
          this.show_modal_direct_access_grant = false
          window.location = '/'
      })
    },
    changePermissions: function() {
      var headers = {
        'Auth-Token': this.token
      }
      var access = {'read':this.read, 'interact':this.interact, 'fork':this.fork}
      var api_str = '/api/accessreqs/'+request_id+'/changepermissions'
      this.$http.patch(api_str, access, {headers: headers}).then((response) => {
        if (response.status == 200)
          this.show_modal_public_permissions_change = false
          window.location = '/'
      })
    },
    dismissModal: function() {
      this.show_modal_direct_access_grant = false
      this.show_modal_public_permissions_change = false
    }
  }
})
