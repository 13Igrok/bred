**Задача 1943 — почта SOGo: не работает поиск в Outlook, лишний пустой черновик**  
**Дата:** 2026-10-08 ·  **Среда:** k3s k3s-prod, namespace mail ·  **Ничего не изменялось, только чтение**  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSeYxZw/lVeDGMACBrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA6fOBdd+dKAKAAAAAElFTkSuQmCC)  
**1. Почему не работает поиск в Outlook — причина найдена и доказана**  
Outlook не связан с SOGo: он ходит по IMAP напрямую в mail/mailserver-360pro  
   
 (dovecot 2.3.19.1). SOGo в вебе ищет по своей базе Postgres, поэтому в браузере  
   
 всё работает. А вот IMAP-поиск отдаёт dovecot:  
/etc/dovecot/conf.d/90-fts-xapian.conf  
   fts_xapian = partial=3 full=20 verbose=0  
   fts_enforced = no  
   
partial=3 full=20 означает: полнотекстовый индекс есть только для писем за  
   
 **3–20 дней**. Всё старше 20 дней индексируется  **только по заголовкам**,  
   
 тело не индексируется. Плюс обратный перекос: свежие письма (0–3 дня) тоже  
   
 без полного текста.  
У ящика a.zagainov@360pro.online в INBOX 2168 писем, из них **2119 старше**  
 **  
 20 дней** — то есть у 97,7% писем тело не ищется.  
**Доказательство** (письмо от 2026-08-03, 65 дней назад):  
doveadm search -u a.zagainov@360pro.online TEXT 2344014566  → 9 совпадений   (слово из ТЕМЫ)  
 doveadm search -u a.zagainov@360pro.online TEXT zzwubwlxp  → 0 совпадений   (слово только из ТЕЛА)  
   
В логах dovecot видно, как Outlook отрабатывает запрос за 0,001 с и получает  
   
 пустой ответ:  
imap(a.zagainov@360pro.online)<2165862>: Disconnected: Connection closed  
   (SEARCH finished 0.001 secs ago) in=142 out=1767 hdr_count=0  
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsScYxpg/h5VMYARvRrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA224BcUMk6pDAAAAAElFTkSuQmCC)  
**2. Что и где менять**  
Правка **внутри пода бесполезна** — конфиг перезаписывается при каждом старте  
   
 контейнера. Менять в одном месте:  
/tmp/docker-mailserver/user-patches.sh   строка 549  
     fts_xapian = partial=3 full=20 verbose=0  
   
Файл лежит на PVC, а не в git:  
PVC mailserver-data (800Gi, StorageClass longhorn-mail)  
   └─ subPath: config → /tmp/docker-mailserver в поде mailserver-360pro-*  
   
Рекомендация: вынести user-patches.sh в репозиторий (там уже 8 копий  
   
 .bak-* с ручным бэкапом), иначе правки теряются.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAABRAsSdYxKa/jL0MIR7FCt5E2BJsmZmt2gMA4C+Otbqr8+sJAACvXQ85SAYUQNBTfQAAAABJRU5ErkJggg==)  
**3. Блокер: снять ограничение нельзя — нет места**  
Filesystem  Size  Used  Avail  Use%  
 /var/mail    788G  704G    84G   90%  
   
По комментарию разработчика в том же user-patches.sh: «~10GB почты → ~4GB  
   
 индексов», т.е. индекс ≈ 40% от объёма почты. На 704 ГБ это **~250–280 ГБ**  
   
 при свободных 84 ГБ.  
| | | |  
|-|-|-|  
| **Вариант** | **Что сделать** | **Итог** |   
| **A. ** **partial=0 full=0** | полный текст по всей почте | не влезает на диск |   
| **B. Расширить PVC → A** | сначала увеличить том | корректно, долго |   
| **C. ** **partial=7 full=365** | полный текст за год | та же нехватка места |   
| **D. Оставить окно** | не править, сообщить пользователям: по старым письмам ищите по теме/отправителю | дёшево, жалобы останутся |   
   
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNhZscVjnidKEAGFtgISaugy8zs1RkAAH9xr9VWHV9PAAB47XoAor8EPg1yCpUAAAAASUVORK5CYII=)  
**4. Порядок работ (после решения по диску)**  
1. Расширить PVC mailserver-data.  
2. user-patches.sh:549 — поменять значение fts_xapian.  
3. Пересобрать индекс (прецедент есть: reindex-kashin-20260814.log,  
 reindex-zurnadzhi-20260813.log в /var/mail/ — в августе делали поштучно):  
doveadm fts rescan -u <user>@360pro.online      # пометить  
 doveadm index     -u <user>@360pro.online '*'   # построить  
 doveadm index -A '*'                            # все 471 ящик — тяжело, порциями  
   
Учесть: service indexer-worker { vsz_limit = 4GB }, I/O на Longhorn.  
   
 Переиндексацию 471 ящика — в ночное окно.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANUlEQVR4nO3OMQ2AABAAsSNBCkJfE1pYGfHAiAU2QtIq6DIzW7UHAMBfnGt1V8fXEwAAXrse4dwF6o2O55YAAAAASUVORK5CYII=)  
**5. Проверка**  
# параметр применился  
 kubectl -n mail exec mailserver-360pro-<pod> -- dovecot -n | grep -A2 fts_xapian  
   
 # решающий тест — должен вернуть совпадение  
 kubectl -n mail exec mailserver-360pro-<pod> -- \  
   doveadm search -u a.zagainov@360pro.online TEXT zzwubwlxp  
   
Из Outlook: найти письмо старше 20 дней по слову из **тела**.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANElEQVR4nO3OQQmAABRAsad4FCtY9ecwnkms4E2ELcGWmTmrKwAA/uLeqrU6vp4AAPDa/gDzUgM9+S8z3AAAAABJRU5ErkJggg==)  
**6. Пустой черновик во вложении — причина не установлена**  
Правок не предлагаю. Серверная часть в порядке: папка \Drafts объявлена  
   
 верно, квоты не заданы, 0-байтных сообщений в .Drafts нет.  
Нужно собрать:  
1. Заголовки MIME-частей письма с вложением от того у кого не работает.  
2. Какой IMAP-адрес настроен в Outlook и включён ли поиск «по всем папкам».  
3. Нет ли у пользователя двух ящиков (в кластере их 5 почтовых серверов:  
 360pro, flash, omicron, omiplat, rocketcom) — с двумя аккаунтами  
   
 на разных серверах Outlook прикладывает старый черновик как вложение.  
 Том на 90%. При полном заполнении APPEND в Drafts начнёт отдавать  
   
 NO [OVERQUOTA], и пустые черновики станут серверной проблемой — мониторить  
   
 отдельно.  
![](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAnEAAAACCAYAAAA3pIp+AAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAANklEQVR4nO3OQQmAABRAsSfYxZo/jzlMYQLPJrCCNxG2BFtmZquOAAD4i3Ot7mr/egIAwGvXA4q7Bc870TqdAAAAAElFTkSuQmCC)  
**7. Сопутствующее (в этот же тикет)**  
| | |  
|-|-|  
| **Что** | **Зачем** |   
| TLS IMAP — ssl-cert-snakeoil.pem, самоподписанный (dovecot -n: ssl_cert) | Outlook предупредит о сертификате; выпустить на mail.360pro.online |   
| Пароль AD svc-mailserver@360pro.online plaintext в user-patches.sh (dnpass, MASTER_HASH) | вынести в Kubernetes Secret |   
| fts не включён для protocol lda/lmtp (предупреждение doveconf) | при доставке через LMTP тело не индексируется автоматически |   
| Порты 25/143/465/587/993 в NodePort мимо traefik | нет L7-фильтрации, ограничить сегментом |   
| Том 90% | блокер для варианта A/C |   
   
