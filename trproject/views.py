from django.shortcuts import render, redirect
from django.views import View
import requests
import time
import concurrent.futures

#  trp\Scripts\activate.bat
global api_key
api_key = 'RGAPI-d3026867-da52-4998-ae30-5d4fbc8ca963'


# Create your views here.
class Index(View):
    def get(self, request):
        return render(request, "TR/index.html")
    def post(self, request):
        region = request.POST['region']
        summoner = request.POST['summoner']
        return redirect("/score/"+region+"/"+summoner)

class Get_Score(View):
    def get(self, request, region, summoner):
        st = time.time() # time check
        stp = time.process_time() # time check

        region = region
        summoner_name = summoner

        # Make the request to the API
        response = requests.get(f'https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}', headers={'X-Riot-Token': api_key})

        # Extract the summoner ID from the response
        data = response.json()
        summoner_id = data['id']
        puuid = data['puuid']


        # Make a request to the League of Legends API to get the player's data
        response = requests.get(f'https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}', headers={'X-Riot-Token': api_key})
        data = response.json()


        response = requests.get(f'https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?queue=420&type=ranked&start=0&count=20', headers={'X-Riot-Token': api_key})
        data = response.json()

        try:
            matchId = data[0]
            response = requests.get(f'https://americas.api.riotgames.com/lol/match/v5/matches/{matchId}', headers={'X-Riot-Token': api_key})
            data_match = response.json()
            if data_match['info']['gameDuration'] < 300:
                matchId = data[1]
                response = requests.get(f'https://americas.api.riotgames.com/lol/match/v5/matches/{matchId}', headers={'X-Riot-Token': api_key})
                data_match = response.json()

            match_info = data_match['info']['participants']
            player_info = next(item for item in match_info if item['puuid'] == puuid)
            p_user = self.Calculate_score(player_info)


            Lane = player_info['teamPosition']


            player_info = next(item for item in match_info if item['teamPosition'] == Lane if item['puuid'] != puuid)
            opp = self.Calculate_score(player_info)

            #print(self.get_average_score(data,puuid))

            gameDuration = data_match['info']['gameDuration']
            gameEndTimestamp = data_match['info']['gameEndTimestamp']

        except Exception as exc:
            print(f'generated an exception: {exc}')
            return render(request, "TR/score.html", {"error":"ERROR"})

        et = time.time()
        etp = time.process_time()
        # get the execution time
        elapsed_time = et - st
        elapsed_timep = etp - stp

        context = {
            "p_user": p_user,
            "opp":opp,
            "gameDuration":gameDuration // 60,
            "elapsed_time":elapsed_time,
            "elapsed_timep":elapsed_timep,
        }

        return render(request, "TR/score.html",context)

    def get_average_score(self, data, puuid):
        def average_score(self, matchId):
            response = requests.get(f'https://americas.api.riotgames.com/lol/match/v5/matches/{matchId}', headers={'X-Riot-Token': api_key})
            return response.json()

        def average_score_per_stat(list_of_dict):
            score_per_stat = {}

            for dict in list_of_dict:
                for k, v in dict.items():
                    if not isinstance(v, str):
                        if k in score_per_stat:
                            score_per_stat[k] += v
                        else:
                            score_per_stat[k] = v
            for k, v in score_per_stat.items():
                score_per_stat[k] = v // len(list_of_dict)

            print("--"*30)
            return score_per_stat

        score_average = []
        match_api_data = []
        list_of_dict_score = []
        list_of_dict_stat = []

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_match = {executor.submit(average_score, self, match): match for match in data}
            for future in concurrent.futures.as_completed(future_to_match):
                matchId = future_to_match[future]
                try:
                    match_data = future.result()
                except Exception as exc:
                    print(f'{matchId} generated an exception: {exc}')
                else:
                    match_api_data.append(match_data)
        for m in match_api_data:
            if m['info']['gameDuration'] > 300:
                match_info = m['info']['participants']
                player_info = next(item for item in match_info if item['puuid'] == puuid)
                p_user = self.Calculate_score(player_info)
                score_average.append(p_user['score'])
                list_of_dict_score.append(p_user['score_per_stat'])
                list_of_dict_stat.append(p_user['context'])
            else:
                pass

        print(average_score_per_stat(list_of_dict_score))
        print(average_score_per_stat(list_of_dict_stat))


        return sum(score_average) // len(score_average)

    def Calculate_score(self, player_info):

        Lane = player_info['teamPosition'] # Get player lane on match

        # ------------------------Variable Paramters----------------------------------------------
        p_assists = 2.5
        p_dmgO = 0.0016
        p_kills = 5.2
        p_cs = 0.25
        p_vscore = 1.5
        p_gpm = 0.095
        p_lanecs = 0.5
        if player_info['challenges']['laneMinionsFirst10Minutes'] >= 70:
            p_lanecs = 0.6
        if player_info['challenges']['laneMinionsFirst10Minutes'] >= 80:
            p_lanecs = 0.75
        if player_info['challenges']['laneMinionsFirst10Minutes'] >= 90:
            p_lanecs = 0.82
        p_solokills = 4.5
        p_plates = 6.8
        p_towers = 13.2
        p_scuttle = 4
        p_saveally = 2
        p_teamP = 1.25
        p_decward = 1.52
        p_outK = 5.5
        p_totalH = 0.004
        p_wards = 0.42
        p_killA = 2.9
        p_dmgM = 0.068
        p_drag = 3.7
        p_baron = 5.2
        p_herald = 2
        p_csA = 1.05
        p_jungleK = 0.25
        p_enemyJK = 1
        p_killP = 0.65
        p_kda = 5.5
        p_dmgC = 0.0010
        p_saveA = 5

        # ------------------------Lane based paramters--------------------------------------------------

        if Lane == "TOP":
            p_lanecs += 0.195
            p_solokills += 5.85
            p_outK += 5.55
            p_csA += 0.65
            p_plates += 1.95
            p_towers += 4.9
            if player_info['challenges']['killParticipation'] * 100 >= 50:
                p_killP += 0.09
            if player_info['challenges']['killParticipation'] * 100 >= 60:
                p_killP += 0.03
            if player_info['challenges']['killParticipation'] * 100 >= 71:
                p_killP += 0.035

        if Lane == "JUNGLE":
            p_jungleK += 0.08
            p_killA += 2.1
            p_drag += 3.8
            p_baron += 4.8
            p_herald += 1.9
            p_enemyJK += 0.8
            p_scuttle += 1.2
            p_killP += 0.46

        if Lane == "MID": # Mid takes less from stats but uses more stats than other lanes
            p_killP += 0.18
            p_dmgO += 0.0008
            p_killA += 1.2
            p_dmgM += 0.03
            p_drag += 1.8
            p_baron += 2.8
            p_herald += 0.9
            p_scuttle += 1.2
            p_solokills += 2.9
            p_lanecs += 0.071
            p_wards += 0.22
            p_teamP += 0.75


        if Lane == "BOTTOM":
            p_teamP += 1
            p_dmgM += 0.055
            p_gpm += 0.11
            p_csA += 0.85
            p_lanecs += 0.295
            p_cs += 0.15
            p_dmgO += 0.0008
            p_dmgC += 0.0006


        if Lane == "SUPPORT":
            p_wards += 1.42
            p_killA += 2.2
            p_killP += 0.48
            p_assists += 4
            p_totalH += 0.008
            p_decward += 2.5
            p_vscore += 2.5
            p_saveA += 5.5


        # ------------------------Calculate Score--------------------------------------------------


        Champ_Level = player_info['champLevel']
        Champ = player_info['championName']
        Win = player_info['win']
        Assists = player_info['assists']
        Damage_to_Objective = player_info['damageDealtToObjectives']
        Kills = player_info['kills']
        Deaths = player_info['deaths']
        Lane = player_info['teamPosition']
        Jungle_mobs_killed = player_info['neutralMinionsKilled']
        CS = player_info['totalMinionsKilled']
        Total_CS = Jungle_mobs_killed + CS
        Vision_Score = player_info['visionScore']
        Gold_per_Minute = player_info['challenges']['goldPerMinute']
        KDA = player_info['challenges']['kda']
        Lane_CS = player_info['challenges']['laneMinionsFirst10Minutes']
        CS_Advantage_On_Lane_Opponent = player_info['challenges']['maxCsAdvantageOnLaneOpponent']
        Solo_Kills = player_info['challenges']['soloKills']
        Plates = player_info['challenges']['turretPlatesTaken']
        Towers_Takedown = player_info['challenges']['turretTakedowns']
        Kill_Participation = player_info['challenges']['killParticipation']
        Dragon_Kills = player_info['dragonKills']
        Baron_Kills = player_info['baronKills']
        Herald_Kills = player_info['challenges']['riftHeraldTakedowns']
        Scuttle_Crab_Kills = player_info['challenges']['scuttleCrabKills']
        Save_Ally_From_Death = player_info['challenges']['saveAllyFromDeath']
        Team_Damage_Percentage = player_info['challenges']['teamDamagePercentage']
        Detector_Wards_Placed = player_info['detectorWardsPlaced']
        Out_Numbered_Kills = player_info['challenges']['outnumberedKills']
        Total_Heals_On_Teammates = player_info['totalHealsOnTeammates']
        Wards_Placed = player_info['wardsPlaced']
        Wards_Killed = player_info['wardsKilled']
        Pick_Kill_With_Ally = player_info['challenges']['pickKillWithAlly']
        More_Enemy_Jungle_Than_Opponent = player_info['challenges']['moreEnemyJungleThanOpponent']
        Enemy_Jungle_Monster_Kills = player_info['challenges']['enemyJungleMonsterKills']
        Damage_Per_Minute = player_info['challenges']['damagePerMinute']
        Dmg_to_Champs = player_info['totalDamageDealtToChampions']

        context = {
            "Champ":Champ,
            "Win":Win,
            "Champ_Level":Champ_Level,
            "Lane":Lane,
            "Kills":round(Kills),
            "Deaths":round(Deaths),
            "Assists": round(Assists),
            "KDA":KDA,
            "Total_CS":round(Total_CS),
            "Lane_CS":round(Lane_CS),
            "CS_Advantage_On_Lane_Opponent":round(CS_Advantage_On_Lane_Opponent),
            "Gold_per_Minute":round(Gold_per_Minute),
            "Kill_Participation":round(Kill_Participation * 100),
            "Team_Damage_Percentage":round(Team_Damage_Percentage * 100),
            "Dmg_to_Champs":round(Dmg_to_Champs),
            "Damage_Per_Minute":round(Damage_Per_Minute),
            "Solo_Kills":round(Solo_Kills),
            "Out_Numbered_Kills":round(Out_Numbered_Kills),
            "Pick_Kill_With_Ally":round(Pick_Kill_With_Ally),
            "Towers_Takedown":round(Towers_Takedown),
            "Plates":round(Plates),
            "Damage_to_Objective":round(Damage_to_Objective),
            "Dragon_Kills":round(Dragon_Kills),
            "Baron_Kills":round(Baron_Kills),
            "Herald_Kills":round(Herald_Kills),
            "Scuttle_Crab_Kills":round(Scuttle_Crab_Kills),
            "Enemy_Jungle_Monster_Kills":round(Enemy_Jungle_Monster_Kills),
            "More_Enemy_Jungle_Than_Opponent":round(More_Enemy_Jungle_Than_Opponent),
            "Detector_Wards_Placed":round(Detector_Wards_Placed),
            "Wards_Placed":round(Wards_Placed),
            "Wards_Killed":round(Wards_Killed),
            "Vision_Score":round(Vision_Score),
            "Total_Heals_On_Teammates":round(Total_Heals_On_Teammates),
            "Save_Ally_From_Death":round(Save_Ally_From_Death),

         }

        Assists = Assists * p_assists
        Damage_to_Objective = Damage_to_Objective * p_dmgO
        Kills = Kills * p_kills
        Deaths = Deaths * p_kills
        Jungle_mobs_killed = Jungle_mobs_killed * p_jungleK
        CS = CS * p_cs
        Total_CS = Jungle_mobs_killed + CS
        Vision_Score = Vision_Score * p_vscore
        Gold_per_Minute = Gold_per_Minute * p_gpm
        KDA = KDA * p_kda
        Lane_CS = Lane_CS * p_lanecs
        CS_Advantage_On_Lane_Opponent = CS_Advantage_On_Lane_Opponent * p_csA
        Solo_Kills = Solo_Kills * p_solokills
        Plates = Plates * p_plates
        Towers_Takedown = Towers_Takedown * p_towers
        Kill_Participation = Kill_Participation * 100 * p_killP
        Dragon_Kills = Dragon_Kills * p_drag
        Baron_Kills = Baron_Kills * p_baron
        Herald_Kills = Herald_Kills * p_herald
        Scuttle_Crab_Kills = Scuttle_Crab_Kills * p_scuttle
        Save_Ally_From_Death = Save_Ally_From_Death * p_saveally
        Team_Damage_Percentage = Team_Damage_Percentage * 100 * p_teamP
        Detector_Wards_Placed = Detector_Wards_Placed * p_decward
        Out_Numbered_Kills = Out_Numbered_Kills * p_outK
        Total_Heals_On_Teammates = Total_Heals_On_Teammates * p_totalH
        Wards_Placed = Wards_Placed * p_wards
        Wards_Killed = Wards_Killed * p_wards
        Pick_Kill_With_Ally = Pick_Kill_With_Ally * p_killA
        More_Enemy_Jungle_Than_Opponent = More_Enemy_Jungle_Than_Opponent * p_jungleK
        Enemy_Jungle_Monster_Kills = Enemy_Jungle_Monster_Kills * p_enemyJK
        Damage_Per_Minute = Damage_Per_Minute * p_dmgM
        Dmg_to_Champs = Dmg_to_Champs * p_dmgC

        score_per_stat = {
            "Kills":round(Kills),
            "Deaths":round(Deaths),
            "Assists": round(Assists),
            "KDA":round(KDA),
            "Total_CS":round(Total_CS),
            "Lane_CS":round(Lane_CS),
            "CS_Advantage_On_Lane_Opponent":round(CS_Advantage_On_Lane_Opponent),
            "Gold_per_Minute":round(Gold_per_Minute),
            "Kill_Participation":round(Kill_Participation),
            "Team_Damage_Percentage":round(Team_Damage_Percentage),
            "Dmg_to_Champs":round(Dmg_to_Champs),
            "Damage_Per_Minute":round(Damage_Per_Minute),
            "Solo_Kills":round(Solo_Kills),
            "Out_Numbered_Kills":round(Out_Numbered_Kills),
            "Pick_Kill_With_Ally":round(Pick_Kill_With_Ally),
            "Towers_Takedown":round(Towers_Takedown),
            "Plates":round(Plates),
            "Damage_to_Objective":round(Damage_to_Objective),
            "Dragon_Kills":round(Dragon_Kills),
            "Baron_Kills":round(Baron_Kills),
            "Herald_Kills":round(Herald_Kills),
            "Scuttle_Crab_Kills":round(Scuttle_Crab_Kills),
            "Enemy_Jungle_Monster_Kills":round(Enemy_Jungle_Monster_Kills),
            "More_Enemy_Jungle_Than_Opponent":round(More_Enemy_Jungle_Than_Opponent),
            "Detector_Wards_Placed":round(Detector_Wards_Placed),
            "Wards_Placed":round(Wards_Placed),
            "Wards_Killed":round(Wards_Killed),
            "Vision_Score":round(Vision_Score),
            "Total_Heals_On_Teammates":round(Total_Heals_On_Teammates),
            "Save_Ally_From_Death":round(Save_Ally_From_Death),

         }

        score = (Assists + Champ_Level + Damage_to_Objective + Kills - Deaths + Total_CS +Vision_Score+ Gold_per_Minute + KDA + Lane_CS + CS_Advantage_On_Lane_Opponent + Solo_Kills + Plates + Towers_Takedown + Kill_Participation
         + Dragon_Kills + Baron_Kills + Herald_Kills + Scuttle_Crab_Kills + Save_Ally_From_Death + Team_Damage_Percentage + Detector_Wards_Placed + Out_Numbered_Kills
         + Total_Heals_On_Teammates + Wards_Placed + Wards_Killed + Pick_Kill_With_Ally + More_Enemy_Jungle_Than_Opponent + Enemy_Jungle_Monster_Kills + Damage_Per_Minute+Dmg_to_Champs)

        response = {"score":round(score), "context":context, "score_per_stat":score_per_stat}
        return response
