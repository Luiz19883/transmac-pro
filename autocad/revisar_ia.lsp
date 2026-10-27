;;; Comandos do revisor de desenhos com IA.
;;;
;;;   REVISARIA      - regras + IA, marca os problemas e abre o relatório
;;;   REVISARREGRAS  - só as regras da empresa (sem custo de IA)
;;;   LIMPARREVISAO  - apaga as marcas da camada REVISAO_IA
;;;   IRHANDLE       - dá zoom numa entidade pelo handle do relatório
;;;
;;; Para carregar sempre: APPLOAD > Conteúdo (Startup Suite) > adicionar este arquivo.

;; Ajuste estes dois caminhos ao seu computador.
(setq *ria-pasta*  "C:\\transmac-pro")   ; pasta com autocad_ia\ e padroes.yaml
(setq *ria-python* "python")             ; ou o caminho completo, ex.: C:\\Python313\\python.exe

(defun ria-executar (opcoes / linha)
  ;; Roda o Python numa janela de console. Ele lê o desenho ativo via COM,
  ;; então não é preciso salvar antes.
  (setq linha
    (strcat "/c cd /d \"" *ria-pasta* "\" && \"" *ria-python* "\" -m autocad_ia "
            opcoes " & pause"))
  (startapp "cmd.exe" linha)
  (princ "\nRevisão iniciada na janela do console. As marcas aparecem na camada REVISAO_IA.")
  (princ))

(defun c:REVISARIA ()
  (ria-executar "--marcar --abrir"))

(defun c:REVISARREGRAS ()
  (ria-executar "--sem-ia --marcar --abrir"))

(defun c:LIMPARREVISAO (/ sel)
  (if (setq sel (ssget "_X" '((8 . "REVISAO_IA"))))
    (progn
      (command "_.ERASE" sel "")
      (princ (strcat "\n" (itoa (sslength sel)) " marca(s) apagada(s).")))
    (princ "\nNenhuma marca de revisão no desenho."))
  (princ))

(defun c:IRHANDLE (/ handle ent)
  (setq handle (getstring "\nHandle da entidade: "))
  (if (setq ent (handent handle))
    (progn
      (command "_.ZOOM" "_OBJECT" ent "")
      (sssetfirst nil (ssadd ent)))
    (princ (strcat "\nHandle " handle " não encontrado.")))
  (princ))

(princ "\nRevisor IA carregado: REVISARIA, REVISARREGRAS, LIMPARREVISAO, IRHANDLE.")
(princ)
