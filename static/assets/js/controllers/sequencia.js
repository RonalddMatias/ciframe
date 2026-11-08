angular.module('deciframeApp').controller('SequenciaController', function($http, $window, ngProgressFactory, $anchorScroll, $location, GENEROS) {
  var COR_ACORDE = '#2E1C74';
  var vm = this;

  vm.sequenciasFamosas = [];
  vm.carregandoCatalogo = true;
  vm.erroCatalogo = false;

  vm.minhaSequencia = {};
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech = "";
  vm.musics = [];
  vm.generos = GENEROS;
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  vm.novaSequencia = { acordes: '', nome: '' };
  vm.cadastrando = false;
  vm.mensagemCadastro = '';
  vm.erroCadastro = '';

  var corpo = function(resposta) {
    if (!angular.isString(resposta.data)) {
      return resposta.data;
    }
    try {
      return angular.fromJson(resposta.data);
    } catch (e) {
      return resposta.data;
    }
  };

  var mapearSequencia = function(sequencia) {
    return {
      id: sequencia.id,
      nome: sequencia.nome,
      acordes: sequencia.acordes.map(function(acorde) {
        return { acorde: acorde, cor: COR_ACORDE };
      })
    };
  };

  var selecionarPorId = function(id) {
    for (var i = 0; i < vm.sequenciasFamosas.length; i++) {
      if (vm.sequenciasFamosas[i].id === id) {
        return vm.sequenciasFamosas[i];
      }
    }
    return null;
  };

  vm.carregarCatalogo = function(idParaSelecionar) {
    vm.carregandoCatalogo = true;
    vm.erroCatalogo = false;

    return $http.get('sequencias').then(function(resposta) {
      vm.sequenciasFamosas = corpo(resposta).map(mapearSequencia);
      vm.carregandoCatalogo = false;

      if (idParaSelecionar) {
        var selecionada = selecionarPorId(idParaSelecionar);
        if (selecionada) {
          vm.pesquisarPorSequencia(selecionada);
        }
      }
    }, function() {
      vm.carregandoCatalogo = false;
      vm.erroCatalogo = true;
    });
  };

  vm.temAcorde = function(acorde) {
    if (vm.minhaSequencia.acordes) {
      return (vm.minhaSequencia.acordes.indexOf(acorde) > -1);
    } else {
      return false;
    }
  }

  vm.pesquisarPorSequencia = function(sequencia) {
    if (sequencia) {
      vm.minhaSequencia = sequencia;
    }
    if (!vm.minhaSequencia.id) {
      return;
    }

    vm.progressbar.start();
    vm.esfigeSpeech = "Procurando músicas com base na sequencia...";
    vm.isSearching = true;
    vm.musics = [];

    var searchString = "similares?sequencia_id=".concat(vm.minhaSequencia.id);
    if (vm.meuGenero !== "" && vm.meuGenero !== null) {
      searchString += "&generos=" + encodeURIComponent(vm.meuGenero);
    }

    $http.get(searchString)
      .then(function(resposta) {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Encontrei essas músicas";
        vm.isSearching = false;
        vm.showSearchResultsCount = true;
        vm.musics = corpo(resposta);
      }, function() {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Ops! Algo errado.";
        vm.isSearching = false;
        vm.showSearchResultsCount = false;
      });
  }

  var separarAcordes = function(texto) {
    return (texto || '').split(/[\s,]+/).filter(function(token) {
      return token.length > 0;
    });
  };

  vm.cadastrarSequencia = function() {
    var acordes = separarAcordes(vm.novaSequencia.acordes);
    var nome = (vm.novaSequencia.nome || '').trim();
    var payload = { acordes: acordes };
    if (nome) {
      payload.nome = nome;
    }

    vm.cadastrando = true;
    vm.mensagemCadastro = '';
    vm.erroCadastro = '';

    $http.post('sequencias', payload).then(function(resposta) {
      vm.cadastrando = false;
      vm.novaSequencia = { acordes: '', nome: '' };
      vm.mensagemCadastro = 'Sequência cadastrada!';
      vm.carregarCatalogo(corpo(resposta).id);
    }, function(resposta) {
      vm.cadastrando = false;
      var erro = corpo(resposta) || {};

      if (resposta.status === 409) {
        vm.mensagemCadastro = 'Essa sequência já existe; selecionando a cadastrada.';
        vm.carregarCatalogo(erro.id);
      } else {
        vm.erroCadastro = erro.erro || 'Não foi possível cadastrar a sequência.';
      }
    });
  };

  vm.limparPesquisa = function() {
    vm.minhaSequencia = {};
    vm.musics = [];
  }

  vm.goToLirics = function(music) {
    $window.open(music.url);
  };

  vm.goToResults = function() {
    vm.showSearchResultsCount = false;
    $("body").animate({scrollTop: $("#results").offset().top}, "slow");
  };

  vm.carregarCatalogo();
});
