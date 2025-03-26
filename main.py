import region as re
import club as cc
import json
import numpy as np



def run(init_coalition, carbon_price, tariff, method, rounds = 20, mu = 1, distribution = 0.5, gdp_method = False, GDP_percent = 1): 
    #Main function of the model, takes as input the initial coalition of club members, a carbon price, a BCA, the method for BCA revenue distribution and a myopia rate (mu, set by default at 1).
    #Possible methods for BCA revenue distribution: equal, export, abatement, WTO
    # If the chosen method is "abatement," the distribution variable can be explicitly defined (set by default at 0.5) to indicate how benefits are distributed among members and non-members.
    #A higher distribution value leads to more benefits for non-members and less for members.
  
    #Creating regions and the club, calling the club and region classes
    GDP_percent = GDP_percent/100
    regions = re.create_regions()
    club, non_members = cc.create_club(regions, init_coalition, tariff, carbon_price)
    regionsname = [region.name for region in regions]
    regionsemissions = [region.e for region in regions]
    regionscp = [region.cp for region in regions]
    status = [[] for _ in range(len(regionsname))]
    implicitcp = {m: cp for m, cp in zip(regionsname, regionscp)}
    previous_abatement = {}
    previous_cost_cp = {}
    potential_cp = {region.name: region.cp for region in regions}
    original_nm = {}; original_m = {}
    remaining_abatement_cost = {}
    prev_remaining_abatement_cost = {}
    i = 0
    previous_revenue_ab = 0
    
    #Importing the data on Marginal Abatement Costs (MAC)
    MACeq = {};   iMACeq = {}
    #MAC2025 = {}; iMAC2025 = {}
    MAC2030 = {}; iMAC2030 = {}
    MAC2040 = {}; iMAC2040 = {}
    MAC2050 = {}; iMAC2050 = {}
    total_abatement_cost = {}
    for region in regions:
        MACeq[region.name], MAC2030[region.name], MAC2040[region.name], MAC2050[region.name] = get_MAC(region)
        iMACeq[region.name], iMAC2030[region.name], iMAC2040[region.name], iMAC2050[region.name] = get_inverseMAC(region)
        total_abatement_cost[region.name] =  region.cost_abatement(club.cp, MACeq[region.name], iMACeq[region.name])

    #initiating the rounds and defining/reinitiating variables
    while i<rounds:       
        #year = i + 2025       
        club_trade_size = calc_size(club.members,non_members)
        print(club_trade_size)
        di = distribution*club_trade_size    
        cm_size = len(club.members) 
        min_cp = min([region.cp for region in regions])
        join_dictm = {}
        join_dictnm = {}
        
        #Launching the appropriate MAC curves for the year in place
        """if year < 2030:    
            MACeq = MAC2025
            iMACeq = iMAC2025
        elif year < 2040:
            MACeq = MAC2030
            iMACeq = iMAC2030
        elif year < 2050:
            MACeq = MAC2040
            iMACeq = iMAC2040
        else:
            MACeq = MAC2050
            iMACeq = iMAC2050"""
            
        #Calculating the exports to the rest of the world and the exports to the club    
        exp_club = {}
        exp_ROW = {}
        for region in regions:
            exp_club[region.name] = exports_club(region,club.members)
            exp_ROW[region.name] = exports_ROW(region, non_members)

        #Calculating the cost of staying out and the abatement costs for joinigng the club for non-members
        total_revenue = 0
        abatement_cost = {}
        cost_staying_nm = {}
        cost_cp = {region.name: 0.0 for region in regions}
        total_abatement_nm = sum(previous_abatement[nm.name] for nm in original_nm)
        for nm in non_members:   
            cost_staying_nm[nm.name] = nm.cost_staying(club.tariff, club.cp, exp_club[nm.name], cm_size, min_cp, method)       
            total_revenue += cost_staying_nm[nm.name]
            if method == "abatement" and gdp_method:
                abatement_cost[nm.name], cost_cp[nm.name], remaining_abatement_cost[nm.name] = returned_gdp_revenues_nm(nm, club.cp, implicitcp[nm.name], total_abatement_cost[nm.name], MACeq[nm.name], iMACeq[nm.name], previous_abatement, previous_cost_cp, previous_revenue_ab, original_nm, total_abatement_nm, prev_remaining_abatement_cost, GDP_percent)
            elif method == "abatement":   
                abatement_cost[nm.name] = returned_revenues(nm, club.cp, MACeq[nm.name], iMACeq[nm.name], previous_abatement, 
                                        previous_revenue_ab, original_nm, total_abatement_nm)
            elif gdp_method:
                abatement_cost[nm.name], cost_cp[nm.name], remaining_abatement_cost[nm.name] = cost_gdp_method_nm(nm, club.cp, implicitcp[nm.name], total_abatement_cost[nm.name], MACeq[nm.name], iMACeq[nm.name], previous_abatement, previous_cost_cp, GDP_percent, prev_remaining_abatement_cost)
            else:
                abatement_cost[nm.name] = nm.cost_abatement(club.cp, MACeq[nm.name], iMACeq[nm.name])
                remaining_abatement_cost[nm.name] = abatement_cost[nm.name]
        for m in club.members:
            if method == "abatement" and gdp_method:
                abatement_cost[m.name], cost_cp[m.name], remaining_abatement_cost[m.name] = return_gdp_revenues(m, club.cp, implicitcp[m.name], total_abatement_cost[m.name], MACeq[m.name], iMACeq[m.name], GDP_percent, prev_remaining_abatement_cost, previous_abatement, previous_revenue_ab, original_nm, total_abatement_nm)
            elif method == "abatement":   
                abatement_cost[m.name] = return_revenues(m, club.cp, MACeq[m.name], iMACeq[m.name], previous_abatement, previous_revenue_ab, original_nm, total_abatement_nm)
            elif gdp_method: #not finished, do not use
                abatement_cost[m.name], cost_cp[m.name], remaining_abatement_cost[m.name] = cost_gdp_method(m, club.cp, implicitcp[m.name], total_abatement_cost[m.name], MACeq[m.name], iMACeq[m.name], GDP_percent, prev_remaining_abatement_cost)
            else:    
                abatement_cost[m.name] = m.cost_abatement(club.cp, MACeq[m.name], iMACeq[m.name])
                remaining_abatement_cost[m.name] = abatement_cost[m.name]
            
        
        previous_abatement = abatement_cost.copy()               
        previous_revenue_ab = sum(cost_staying_nm.values())*di
        prev_remaining_abatement_cost = remaining_abatement_cost.copy()
        previous_cost_cp = cost_cp.copy()
        
        
        #saving the members and non-members of the club in each round
        original_nm = [region for region in non_members]
        original_m = [region for region in club.members]
        
        #cost-benefit analysis for memebrs of the club using the cost_analysis_m function
        for m in original_m:
            print("Name:", m.name)            
            print("Carbon price:", m.cp, "US-$/tCO2")
            potentialm = [ms for ms in original_m if ms != m]
            #potential_cp_original = calc_original_cp(originalcp, potentialm)
            cost = cost_analysis_m(m, exp_club[m.name], exp_ROW[m.name], cost_staying_nm, abatement_cost,
                                   implicitcp[m.name], club_trade_size, cm_size, method, club, original_nm, original_m, mu, di, min_cp, cost_cp[m.name], remaining_abatement_cost[m.name])
            join_dictm[m.name] = cost
            status[regionsname.index(m.name)].append(1)
            #if costs are higher than the benefits region m leaves the club:
            if join_dictm[m.name]>0: #and i>0:
               non_members.append(m)
               club.members = [region for region in club.members if region != m]
               print("LEAVING THE CLUB")
            else: 
                m.cp = club.cp
            print("")
        
        #cost-benefit analysis for non-members of the club
        print("Non Members:")
        for nm in original_nm:
            print("Name:", nm.name)
            print("Carbon price:", nm.cp, "US-$/tCO2")
            #potentialnm = [nms for nms in original_nm if nms != nm]
            potentialm = original_m.copy()
            potentialm.append(nm)
            #pt_club_trade_size = calc_size(potentialm,potentialnm)
            #pt_cp_original = calc_original_cp(originalcp, potentialm)  
            #pt_di = distribution*pt_club_trade_size       
            #print(nm.name, ":", pt_di)
            cost = cost_analysis(nm, exp_ROW[nm.name], cost_staying_nm, abatement_cost, implicitcp[nm.name],
                                 club_trade_size, potentialm, cm_size, method, club, original_nm, mu, di, cost_cp[nm.name], remaining_abatement_cost[nm.name])
            join_dictnm[nm.name] = cost
            status[regionsname.index(nm.name)].append(0)
            #if benefits are higher than the costs region nm joins the club:
            if join_dictnm[nm.name]<=0:
                club.members.append(nm)
                non_members = [region for region in non_members if region != nm]
                print("ENTERING THE CLUB")
            print("")
        
        #Saving the membership status of regions this round
        istatus=[sublist[i] for sublist in status]
        iprevstatus=[sublist[i-1] for sublist in status]
        #stopping the code if stability is reached (full club, empty club or no changes in two consecutive rounds)
        if all(s == 0 for s in istatus) or all(s == 1 for s in istatus):
            break        
        if i>1 and istatus == iprevstatus:
            status = [sublist[:-1] for sublist in status]
            break            
        i += 1

    
    return regionsname, regionsemissions, status


def cost_analysis(region, exp_ROW, cost_staying_nm, abatement_cost_nm, implicitcp, club_trade_size, potentialm, cm_size, method, club, original_nm, mu, di, cost_cp, remaining_abatement_cost):
    print(club_trade_size)
    #Cost-benefit analysis for non-members of the club
    abatement_cost = abatement_cost_nm[region.name]
    cost_staying = cost_staying_nm[region.name]    
    loss_competitiveness = region.cost_competitiveness_nm(club.cp, club_trade_size, exp_ROW, original_nm, implicitcp)
    cost_income = region.cost_income(club.cp, implicitcp, club_trade_size, original_nm)
    cost_joining =  abatement_cost + loss_competitiveness + cost_income + cost_cp
    benefit_joining = calc_benefit_joining(region, potentialm, method, cm_size, original_nm, cost_staying_nm, di)
    
    print(f"""    
    Cost of staying out: {cost_staying}
    Abatement cost: {abatement_cost}
    Direct cost of carbon price: {cost_cp}
    Total cost of carbon price: {(abatement_cost) + (cost_cp)}
    Total abatement cost: {remaining_abatement_cost}
    Loss of competitiveness = {loss_competitiveness}
    Income cost: {cost_income}
    Implicit carbon price: {implicitcp}
    Potential club trade size: {club_trade_size}
    Cost of joining:     {cost_joining}
    Benefit of joining:  {benefit_joining}
    Net cost of joining: {cost_joining - (mu * benefit_joining)}
    Net cost of staying out: {(mu * cost_staying)}
    Net joining - staying out: {int(cost_joining - (mu * benefit_joining) - (mu * cost_staying))} """) 


    return int(cost_joining - (mu * benefit_joining) - (mu * cost_staying))

def cost_analysis_m(region, exp_club, exp_ROW, cost_staying_nm, abatement_cost, implicitcp, club_trade_size, cm_size, method, club, original_nm, original_m, mu, di, min_cp, cost_cp, remaining_abatement_cost):
#Cost-benefit analysis for members of the club
    cost_leaving = region.cost_leaving(club.tariff, club.cp, exp_club, cm_size, min_cp, method) #needs to be changed and adapted for club members
    abatement_cost = abatement_cost[region.name]
    loss_competitiveness = region.cost_competitiveness(club.cp, club_trade_size, exp_ROW, original_nm, implicitcp)
    cost_income = region.cost_income(club.cp, implicitcp, club_trade_size, original_nm)
    cost_staying_in =  abatement_cost + loss_competitiveness + cost_income + cost_cp    
    benefit_staying_in = calc_benefit_staying_in(region, original_m, method, cm_size, original_nm, cost_staying_nm, di) 

    print(f"""
    Cost of leaving: {cost_leaving}
    Abatement cost: {abatement_cost}
    Direct cost of carbon price: {cost_cp}
    Total cost of carbon price: {(abatement_cost) + (cost_cp)}
    Total abatement cost: {remaining_abatement_cost}
    Loss of competitiveness: {loss_competitiveness}
    Income cost: {cost_income}
    Cost of staying in:     {cost_staying_in}
    Benefit of staying in:  {benefit_staying_in}
    Net cost of staying in: {cost_staying_in - (mu * benefit_staying_in)}
    Net cost of leaving: {(mu * cost_leaving)}
    Net staying in - leaving: {int(cost_staying_in - (mu * benefit_staying_in) - (mu * cost_leaving))} """) 


    return int(cost_staying_in - (mu * benefit_staying_in) - (mu * cost_leaving))

def cost_gdp_method_nm(region, club_cp, implicitcp, total_abatement_cost, MACeq, iMACeq, previous_abatement, previous_cost_cp, GDP_percent, prev_remaining_abatement_cost):
    
    if region.cp >= club_cp:    #Region already meets or exceeds the club carbon price                
        abatement_cost = 0.0
        cost_cp = 0.0
        remaining_abatement_cost_region = 0.0
        
    elif region.name in prev_remaining_abatement_cost:
        # Use previous values if available
        abatement_cost = previous_abatement[region.name]
        cost_cp = previous_cost_cp[region.name]
        remaining_abatement_cost_region = prev_remaining_abatement_cost[region.name]
    else:
        remaining_abatement_cost_region = total_abatement_cost
        abatement_payment = region.gdp * GDP_percent  # Investment based on GDP
        #print(region.name, " : ", abatement_payment)

        if remaining_abatement_cost_region <= abatement_payment:
            cost_cp = 0.0
            abatement_cost = remaining_abatement_cost_region
        else:
            potential_paid_abatement = total_abatement_cost - remaining_abatement_cost_region + abatement_payment
            potential_cp = region.find_carbon_price(potential_paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
            abatement_cost = abatement_payment
            cost_cp = region.rest_cost_cp(iMACeq, club_cp, potential_cp)

    return abatement_cost, cost_cp, remaining_abatement_cost_region
    
def returned_revenues (region, club_cp, MACeq, iMACeq, previous_abatement, 
                        previous_revenue_ab, original_nm, total_abatement_nm):                 
        if region.cp >= club_cp:                    
            abatement_cost = 0
        else:    
            if region.name in previous_abatement:                        
                if region in original_nm:
                    if total_abatement_nm == 0:
                        abatement_cost = 0
                    else:
                        share = previous_abatement[region.name]/total_abatement_nm
                        abatement_cost = previous_abatement[region.name] - previous_revenue_ab*share 
                else:    
                    abatement_cost = previous_abatement[region.name]
            else:
                abatement_cost = region.cost_abatement(club_cp, MACeq, iMACeq)
        if abatement_cost < 0:
            abatement_cost = 0
   
        return abatement_cost   
    
def returned_gdp_revenues_nm(region, club_cp, implicitcp, total_abatement_cost, MACeq, iMACeq, previous_abatement, previous_cost_cp, previous_revenue_ab, original_nm, total_abatement_nm, prev_remaining_abatement_cost, GDP_percent):
    if region.cp >= club_cp:    #Region already meets or exceeds the club carbon price                
        abatement_cost = 0.0
        cost_cp = 0.0
        remaining_abatement_cost_region = 0.0
        
    elif region.name in prev_remaining_abatement_cost:
        if region in original_nm: #The region remains outside the club
            if total_abatement_nm == 0:
                #All costs covered by club members
                abatement_cost = 0.0
                cost_cp = 0.0
                remaining_abatement_cost_region = 0.0
            else:
                share = previous_abatement[region.name] / total_abatement_nm
                print(region.name, share, previous_revenue_ab, previous_revenue_ab * share)
                remaining_abatement_cost_region = max(prev_remaining_abatement_cost[region.name] - previous_revenue_ab * share, 0.0)
                #print(region.name, remaining_abatement_cost_region)
                abatement_payment = region.gdp * GDP_percent  # Investment based on GDP
                if remaining_abatement_cost_region <= abatement_payment:
                    cost_cp = 0.0
                    abatement_cost = remaining_abatement_cost_region
                else: 
                    potential_paid_abatement = total_abatement_cost - remaining_abatement_cost_region + abatement_payment
                    potential_cp = region.find_carbon_price(potential_paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
                    abatement_cost = abatement_payment
                    cost_cp = region.rest_cost_cp(iMACeq, club_cp, potential_cp)

        else:
            #The region has left the club: retain previous costs
            abatement_cost = previous_abatement[region.name]
            cost_cp = previous_cost_cp[region.name]
            remaining_abatement_cost_region = prev_remaining_abatement_cost[region.name]
    
    else:
        #First round of the club: calculate full abatement costs
        remaining_abatement_cost_region = total_abatement_cost
        abatement_payment = region.gdp * GDP_percent  # Investment based on GDP

        if remaining_abatement_cost_region < abatement_payment:
            cost_cp = 0.0
            abatement_cost = remaining_abatement_cost_region
        else:
            potential_cp = region.find_carbon_price(abatement_payment, MACeq, iMACeq, implicitcp, club_cp)
            abatement_cost = abatement_payment
            cost_cp = region.rest_cost_cp(iMACeq, club_cp, potential_cp)
    
    return abatement_cost, cost_cp, remaining_abatement_cost_region    

    

def cost_gdp_method(region, club_cp, implicitcp, total_abatement_cost, MACeq, iMACeq, GDP_percent, prev_remaining_abatement_cost): #notfinished
    if region.cp >= club_cp:                    
        abatement_cost = 0.0
        cost_cp = 0.0
        remaining_abatement_cost_region = 0.0   
    elif region.name in prev_remaining_abatement_cost:
        abatement_payment = region.gdp*GDP_percent
        remaining_abatement_cost_region = max(prev_remaining_abatement_cost[region.name] - abatement_payment, 0.0)
        if 0.0 < remaining_abatement_cost_region < abatement_payment:
            cost_cp = 0.0
            abatement_cost = remaining_abatement_cost_region
            paid_abatement = total_abatement_cost - remaining_abatement_cost_region
            region.cp = region.find_carbon_price(paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
        elif remaining_abatement_cost_region == 0:
            cost_cp = 0.0
            abatement_cost = 0.0
            region.cp = club_cp
        else:
            paid_abatement = total_abatement_cost - remaining_abatement_cost_region
            region.cp = region.find_carbon_price(paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
            abatement_cost = abatement_payment
            potential_paid_abatement = total_abatement_cost - remaining_abatement_cost_region + abatement_payment
            potential_cp = region.find_carbon_price(potential_paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
            cost_cp = region.rest_cost_cp(iMACeq, club_cp, potential_cp)                                          
    else:
        remaining_abatement_cost_region = total_abatement_cost
        abatement_payment = region.gdp*GDP_percent            
        #m_cp[region.name] = region.find_carbon_price(abatement_payment, MACeq[region.name], iMACeq[region.name], club.cp)
        if remaining_abatement_cost_region < abatement_payment:
            cost_cp = 0.0
            abatement_cost = remaining_abatement_cost_region
        else:
            potential_cp = region.find_carbon_price(abatement_payment, MACeq, iMACeq, implicitcp, club_cp)
            abatement_cost = abatement_payment
            cost_cp = region.rest_cost_cp(iMACeq, club_cp, potential_cp)
            
    return abatement_cost, cost_cp, remaining_abatement_cost_region 



def return_revenues(region, club_cp, MACeq, iMACeq, previous_abatement, previous_revenue_ab, original_nm, total_abatement_nm):
    if region.cp >= club_cp:                    
        abatement_cost = 0
    else:    
        if region.name in previous_abatement:
            if region in original_nm:
                if total_abatement_nm == 0:
                    abatement_cost = 0
                else:
                    share = previous_abatement[region.name]/total_abatement_nm
                    abatement_cost = previous_abatement[region.name] - previous_revenue_ab*share
            else:    
                abatement_cost = previous_abatement[region.name]
        else:
            abatement_cost = region.cost_abatement(club_cp, MACeq, iMACeq)
    if abatement_cost < 0:
        abatement_cost = 0
    return abatement_cost


def return_gdp_revenues(region, club_cp, implicitcp, total_abatement_cost, MACeq, iMACeq, GDP_percent, prev_remaining_abatement_cost, previous_abatement, previous_revenue_ab, original_nm, total_abatement_nm):
    if region.cp >= club_cp:                    
        abatement_cost = 0.0
        cost_cp = 0.0
        remaining_abatement_cost_region = 0.0
    elif region in original_nm:
            if total_abatement_nm == 0:
                abatement_cost = 0.0
                cost_cp = 0.0
                region.cp = club_cp
                remaining_abatement_cost_region = 0.0
            else: 
                share = previous_abatement[region.name]/total_abatement_nm
                print(region.name, share, previous_revenue_ab)
                remaining_abatement_cost_region =  max(prev_remaining_abatement_cost[region.name] - previous_revenue_ab * share, 0.0)
                abatement_payment = region.gdp*GDP_percent
                if 0.0 < remaining_abatement_cost_region < abatement_payment:
                    cost_cp = 0.0
                    abatement_cost = remaining_abatement_cost_region
                    paid_abatement = total_abatement_cost - remaining_abatement_cost_region
                    region.cp = region.find_carbon_price(paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
                elif remaining_abatement_cost_region == 0:
                    cost_cp = 0.0
                    abatement_cost = 0.0
                    region.cp = club_cp
                else:
                    paid_abatement = total_abatement_cost - remaining_abatement_cost_region
                    region.cp = region.find_carbon_price(paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
                    abatement_cost = abatement_payment
                    potential_paid_abatement = total_abatement_cost - remaining_abatement_cost_region + abatement_payment
                    potential_cp = region.find_carbon_price(potential_paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
                    cost_cp = region.rest_cost_cp(iMACeq, club_cp, potential_cp)   
    elif region.name in prev_remaining_abatement_cost: 
                abatement_payment = region.gdp*GDP_percent
                remaining_abatement_cost_region = max(prev_remaining_abatement_cost[region.name] - abatement_payment, 0.0)
                if 0.0 < remaining_abatement_cost_region < abatement_payment:
                    cost_cp = 0.0
                    abatement_cost = remaining_abatement_cost_region
                    paid_abatement = total_abatement_cost - remaining_abatement_cost_region
                    region.cp = region.find_carbon_price(paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
                elif remaining_abatement_cost_region == 0:
                    cost_cp = 0.0
                    abatement_cost = 0.0
                    region.cp = club_cp
                else:
                    paid_abatement = total_abatement_cost - remaining_abatement_cost_region
                    region.cp = region.find_carbon_price(paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
                    abatement_cost = abatement_payment
                    potential_paid_abatement = total_abatement_cost - remaining_abatement_cost_region + abatement_payment
                    potential_cp = region.find_carbon_price(potential_paid_abatement, MACeq, iMACeq, implicitcp, club_cp)
                    cost_cp = region.rest_cost_cp(iMACeq, club_cp, potential_cp)    
    else:
        remaining_abatement_cost_region = total_abatement_cost
        abatement_payment = region.gdp*GDP_percent                               
        if remaining_abatement_cost_region < abatement_payment:
                cost_cp = 0.0
                abatement_cost = remaining_abatement_cost_region
        else:
                potential_cp = region.find_carbon_price(abatement_payment, MACeq, iMACeq, implicitcp, club_cp)
                abatement_cost = abatement_payment
                cost_cp = region.rest_cost_cp(iMACeq, club_cp, potential_cp)
                
    return abatement_cost, cost_cp, remaining_abatement_cost_region 
        


def get_MAC(region): #x):
    #Open the file with the MACC coefficients
    f = open('mac.json') 
    MACs = json.load(f)
    c1 = MACs['2025'][region.name] #MACC 2025
    c2 = MACs['2030'][region.name] #MACC 2030
    c3 = MACs['2040'][region.name] #MACC 2040
    c4 = MACs['2050'][region.name] #MACC 2050

    return np.poly1d(c1),np.poly1d(c2),np.poly1d(c3),np.poly1d(c4) #(x) #poly1d crea un polinomio con los valores que se le asignan

def get_inverseMAC(region): #x):
    #Open the file with the coefficients for the inverse MACC)
    f = open('invertedmac.json') 
    MACs = json.load(f)
    c1 = MACs['2025'][region.name] #MACC 2025
    c2 = MACs['2030'][region.name] #MACC 2030
    c3 = MACs['2040'][region.name] #MACC 2040
    c4 = MACs['2050'][region.name] #MACC 2050

    return np.poly1d(c1),np.poly1d(c2),np.poly1d(c3),np.poly1d(c4) #(x) #poly1d crea un polinomio con los valores que se le asignan


def exports_club(region,club_members):
    #calculates the percentage of a region's trade that is within the club
    exports = sum(region.trade_partners[m.name] for m in club_members)

    return exports 


def exports_ROW(region,non_members): 
    #calculates the percentage of a region's trade that is outside the club
    exports = sum(region.trade_partners[nm.name] for nm in non_members)

    return exports

def calc_size(members,non_members):
    # Calculates the relative size of the club compared to non-members, in terms of trade.
    total_row = 0
    for region in members: #club trade with the rest of the world
        total_row += sum(region.trade_partners[reg.name] for reg in non_members)

    for region in non_members: #rest of the world trade with the rest of the world
        total_row += sum(region.trade_partners[reg.name] for reg in non_members) 
        #añade al segundo total_row el valor del primero con +=

    total_club = 0
    for region in members: #club trade with the club
        total_club += sum(region.trade_partners[reg.name] for reg in members)

    for region in non_members: #rest of the world trade with the club
        total_club += sum(region.trade_partners[reg.name] for reg in members)

    return total_row / (total_row + total_club)

def calc_original_cp(originalcp,clubmembers): # Based on GDP
    #GDP-weighted average of the original (implicit) carbon price of all members.
    cps, gdps= [], []
    for m in clubmembers:
      #  if m.gdp is None:
      #      m.gdp = 0
        cps.append(originalcp[m.name])
        gdps.append(m.gdp)
       
    tot_gdp, avg_gdp = sum(gdps), 0
    for i, cp in enumerate(cps):
        avg_gdp += cp * (gdps[i] / tot_gdp)

    return avg_gdp

def calc_benefit_joining(region, potentialm, method, cm_size, non_members, cost_staying_nm, di): 
    #Benefits of joining the club
    revenue = 0
    #equal revenue distribution method
    if method == "equal":
        for nm in non_members:
            if nm != region: 
                revenue += cost_staying_nm[nm.name]
        return revenue / (cm_size + 1)
    if method == "gdp":
      for nm in non_members:
            if nm != region: 
                revenue += cost_staying_nm[nm.name]
      gdpshare = region.gdp/sum(m.gdp for m in potentialm)
      return revenue*gdpshare
    #export or WTO renenue distribution methods
    elif method == "export" or method == "WTO":    
        for nm in non_members:
            if nm != region:
                share = nm.trade_partners[region.name]/(sum(nm.trade_partners[m.name] for m in potentialm))
                revenue += share*cost_staying_nm[nm.name]  
        return revenue
    #returning part of the revenue to non-members for abatement costs method
    elif method == "abatement":
        for nm in non_members:
            if nm != region:
                share = nm.trade_partners[region.name]/(sum(nm.trade_partners[m.name] for m in potentialm))
                revenue += share*cost_staying_nm[nm.name]   
        return revenue*(1-di) 
    else:
        raise Exception("No other methods implemented.")
        

def calc_benefit_staying_in(region, club_members, method, cm_size, non_members, cost_staying_nm, di): #I am doing the same as in calc_benefit_joining but dividing among members
    #Benefits of being in the club
    revenue = 0
    #equal revenue distribution method
    if method == "equal":
      revenue = sum(cost_staying_nm[nm.name] for nm in non_members)
      return revenue / (cm_size)
    
    if method == "gdp":
      revenue = sum(cost_staying_nm[nm.name] for nm in non_members)
      gdpshare = region.gdp/sum(m.gdp for m in club_members)
      return revenue*gdpshare
    
    #export or WTO renenue distribution methods
    elif method == "export" or method == "WTO": 
      for nm in non_members:
              share = nm.trade_partners[region.name]/sum(nm.trade_partners[m.name] for m in club_members) 
              revenue += share*cost_staying_nm[nm.name] 
      return revenue 
  
    #returning part of the revenue to non-members for abatement costs method
    elif method == "abatement":
      for nm in non_members:
              share = nm.trade_partners[region.name]/sum(nm.trade_partners[m.name] for m in club_members) 
              revenue += share*cost_staying_nm[nm.name]   
      return revenue*(1-di)         
        
    
    else:
        raise Exception("No other methods implemented.")

