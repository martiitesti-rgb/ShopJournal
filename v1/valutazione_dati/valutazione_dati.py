import pandas as pd
import numpy as np
import os
import math
import csv

def estrai_top_ten(candidates_df, query_id, flag):
    prodotti={}
    top_ten = []
    for row in candidates_df.itertuples():
      q, f= row.query_id, row.source
      if q == query_id and f == flag:
         prodotti[row.rank]= row.asin

    for r in sorted(prodotti.keys()):
       top_ten.append(prodotti[r])
          
    return top_ten

def label_da_top_ten(top_ten,qrels_lookup,query_id):
    labels = []
    for asin in top_ten:
       label = qrels_lookup.get(query_id, {}).get(asin, None)
       if label is None:
            raise ValueError(f"Nessun label trovato per query={query_id}, asin={asin}")
       
       labels.append(label)

    return labels

def recall_at_10(labels_top10, query_id, qrels_lookup):
   numeratore = sum(1 for i in labels_top10 if i >= 1)

   denumeratore = sum(1 for i in qrels_lookup[query_id].values() if i >= 1)

   if denumeratore == 0:
        return 0.0

   return numeratore / denumeratore

def dcg(labels):
    somma = 0.0
    for posizione, label in enumerate(labels, start=1):
        gain = 2**label - 1
        somma += (gain / math.log2(posizione + 1))
    return somma

def ndcg_at_10(labels_top10, query_id, qrels_lookup):
    dcg_reale = dcg(labels_top10)
    # 1. prendi tutti i label disponibili nel pool per questa query
    label_ideali=sorted(qrels_lookup[query_id].values(),reverse=True)[:10]
   
    idcg=dcg(label_ideali)
    if idcg == 0:
        return 0.0
    
    return dcg_reale / idcg
   
def main() :
     #carico i file CSV
     candidates_df = pd.read_csv("/Users/martitesti/Desktop/uni/tesi/ShopJournal/valutazione_dati/system_candidates.csv")
     qrels_df = pd.read_csv("/Users/martitesti/Desktop/uni/tesi/ShopJournal/valutazione_dati/qrels_v1.csv")
     second_round_df = pd.read_csv("/Users/martitesti/Desktop/uni/tesi/ShopJournal/evaluation_test/fase3.2/second_round_output/second_round_labelling_blind.csv", delimiter=";")
     # concateno qrels_v1.csv e second_round_labelling_blind.csv in un unico DataFrame così che ho tutti i prodotti valutati in un unico DataFrame
     qrels_completo = pd.concat([qrels_df, second_round_df], ignore_index=True)

     #check se ci sono duplicati
     duplicati = qrels_completo.duplicated(subset=["query_id", "asin"], keep=False)
     print(qrels_completo[duplicati])    

    #creo un dizionario per ogni query per accedere ai prodotti estraendo solo asin e query_id e label cosi che posso recuoerare direttamente il label conoscendo il prodotto
     qrels_lookup = {}

     for row in qrels_completo.itertuples():
      q, a, l = row.query_id, row.asin, row.label
      if q not in qrels_lookup:
          qrels_lookup[q] = {}
      qrels_lookup[q][a] = l
      #print(qrels_lookup)
     
     #print(len(qrels_lookup))
     #print(sorted(qrels_lookup.keys()))

     #test estraggo le top ten per ogni flag
     #top10 = estrai_top_ten(candidates_df, "q03", "query_only")
     #print(top10)
     #print(len(top10))

     #test label da top ten
     #labels = label_da_top_ten(top10, qrels_lookup, "q03")
     #print(labels)
     #print(len(labels))

     #test recall at 10
     #recall = recall_at_10(labels, "q03", qrels_lookup)
     #print(recall)
     #print(len(qrels_lookup["q03"]))
     #print(sum(1 for v in qrels_lookup["q03"].values() if v >= 1))
     #print(dcg([2, 1, 2]))

     #ndcg= ndcg_at_10(labels,"q03",qrels_lookup)
     #print(ndcg)

     flags = ["query_only", "query_notes", "query_notes_pop", "query_notes_pop_cue"]
     query_ids = sorted(qrels_lookup.keys())  

     risultati= []

     for query_id in query_ids:
         for flag in flags:
             top_ten=estrai_top_ten(candidates_df,query_id, flag)
             labels=label_da_top_ten(top_ten,qrels_lookup,query_id)
             recall=recall_at_10(labels,query_id,qrels_lookup)
             ndcg=ndcg_at_10(labels,query_id,qrels_lookup)

             risultati.append({
                 "query_id":query_id,
                 "flag":flag,
                 "Recall@10":recall,
                 "NDCG@10":ndcg
                })

     risultati_df=pd.DataFrame(risultati)
     print(risultati_df)

     fieldnames = [
         "query_id", "flag", "Recall@10", "NDCG@10"
        ]

     with open("/Users/martitesti/Desktop/uni/tesi/ShopJournal/valutazione_dati/risultati_metriche.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(risultati)

     medie_per_variante = risultati_df.groupby("flag")[["Recall@10", "NDCG@10"]].mean()
     print(medie_per_variante)

     top10_only = estrai_top_ten(candidates_df, "q09", "query_only")
     top10_pop = estrai_top_ten(candidates_df, "q09", "query_notes_pop")

     print("Solo in query_only:", set(top10_only) - set(top10_pop))
     print("Solo in query_notes_pop:", set(top10_pop) - set(top10_only))

     solo_query_only = {'B086GFHDG8', 'B000O0GLUO', 'B09GN2JNY2', 'B00WN13AJC', 'B000REP3P6', 'B077THJ5SB', 'B074H6MCKB', 'B000YQLMQG', 'B01H2JGSB6'}
     solo_query_notes_pop = {'B01AZXXZTY', 'B01N0RKWNM', 'B000REQBZW', 'B08SY8GYBK', 'B000O0GLSQ', 'B000REND9Y', 'B01AZXUK60', 'B00B2AO8B4', 'B000YFZVTG'}

     print("Label dei prodotti persi (erano in query_only, escono con notes_pop):")
     for asin in solo_query_only:
         print(asin, qrels_lookup["q09"].get(asin, "NON GIUDICATO"))

     print("\nLabel dei prodotti guadagnati (entrano con notes_pop):")
     for asin in solo_query_notes_pop:
            print(asin, qrels_lookup["q09"].get(asin, "NON GIUDICATO"))     

     
    

if __name__ == "__main__":
    main()